import hashlib
import json
import re
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.config import settings
from app.core.rate_limit import limiter, get_trusted_client_ip
from app.models.quotation import Quotation, QuotationRevision
from app.models.settings import CompanySettings
from app.models.sharing import QuotationShareLink, SharedQuotationAccessLog, ShareAccessEventType
from app.models.base import utc_now
from app.services.quotation_artifact_service import QuotationArtifactService

router = APIRouter(prefix="/public/quotations", tags=["Public Customer Quotation"])

def normalize_quotation_slug(quote_num: str) -> str:
    if not quote_num:
        return ""
    return re.sub(r"[^a-zA-Z0-9]+", "-", quote_num.strip()).strip("-").upper()

def validate_quotation_number_match(link: QuotationShareLink, requested_quotation_number: str | None = None):
    if requested_quotation_number:
        req_norm = normalize_quotation_slug(requested_quotation_number)
        actual_norm = normalize_quotation_slug(link.quotation.quotation_number) if link.quotation else ""
        if req_norm != actual_norm:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quotation link is invalid or does not match quotation number."
            )

def get_link_by_code_or_token(identifier: str, db: Session) -> QuotationShareLink:
    if not identifier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quotation link is invalid or has been revoked."
        )

    clean_id = identifier.strip()

    # 1. First, try looking up by short_code
    link = db.query(QuotationShareLink).filter(
        QuotationShareLink.short_code == clean_id
    ).first()

    # 2. If not found by short_code and length >= 16, try looking up by SHA-256 token hash (legacy)
    if not link and len(clean_id) >= 16:
        token_hash = hashlib.sha256(clean_id.encode("utf-8")).hexdigest()
        link = db.query(QuotationShareLink).filter(
            QuotationShareLink.token_hash == token_hash
        ).first()

    if not link or link.is_revoked:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quotation link is invalid or has been revoked."
        )

    return link

def get_link_by_token(token: str, db: Session) -> QuotationShareLink:
    return get_link_by_code_or_token(token, db)

def record_access_event(link: QuotationShareLink, event_type: str, request: Request, db: Session):
    try:
        client_ip = get_trusted_client_ip(request)
        salt = settings.SECRET_KEY[:16] if getattr(settings, "SECRET_KEY", None) else "lg_privacy_salt"
        ip_hash = hashlib.sha256(f"{client_ip}_{salt}".encode("utf-8")).hexdigest()[:16] if client_ip else None
        user_agent = request.headers.get("user-agent", "")[:500]

        access_log = SharedQuotationAccessLog(
            share_link_id=link.id,
            event_type=event_type,
            ip_hash=ip_hash,
            user_agent=user_agent
        )
        db.add(access_log)
        link.last_accessed_at = utc_now()
        db.commit()
    except Exception:
        db.rollback()

@router.get("/{token}")
@limiter.limit("60/minute")
def get_public_quotation_details(
    token: str,
    request: Request,
    response: Response,
    quotation_number: str | None = None,
    db: Session = Depends(get_db)
):
    """
    Public customer endpoint to fetch high-level quotation metadata.
    Does not expose internal database IDs, agent-only notes, or private storage details.
    """
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    link = get_link_by_token(token, db)
    validate_quotation_number_match(link, quotation_number)
    record_access_event(link, ShareAccessEventType.VIEW.value, request, db)

    quotation = link.quotation
    revision = link.revision

    # Calculate dates & validity from historical snapshot if present
    created_dt = revision.created_at or datetime.now(timezone.utc)
    issue_date_str = created_dt.strftime("%d-%m-%Y")

    snap_company = {}
    if revision.company_snapshot:
        try:
            snap_company = json.loads(revision.company_snapshot)
        except Exception:
            pass

    company_settings = db.query(CompanySettings).order_by(CompanySettings.version.desc()).first()
    validity_days = snap_company.get("quotation_validity_days") or (company_settings.quotation_validity_days if company_settings else 15)
    expiry_dt = created_dt.timestamp() + (validity_days * 86400)
    expiry_date_str = datetime.fromtimestamp(expiry_dt, tz=timezone.utc).strftime("%d-%m-%Y")

    # Safe public line items
    items_data = [
        {
            "product_name": item.product_name,
            "sku": item.sku,
            "description": item.description,
            "quantity": item.quantity,
            "unit_price": float(item.unit_price),
            "total_price": float(item.total_price),
            "image_url": item.image_url or (item.product.image_url if item.product else None)
        }
        for item in revision.items
    ]

    clean_quote_num = re.sub(r"[^a-zA-Z0-9]+", "-", (quotation.quotation_number or "QUOTE").strip()).strip("-")

    code = link.short_code or token
    pdf_download_url = f"/api/v1/public/quotations/q/{clean_quote_num}/{code}/pdf" if link.short_code else f"/api/v1/public/quotations/{clean_quote_num}/{token}/pdf"

    return {
        "quotation_number": quotation.quotation_number or "QUOTATION",
        "revision_label": revision.revision_label,
        "customer_name": quotation.customer_name,
        "issue_date": issue_date_str,
        "validity_days": validity_days,
        "expiry_date": expiry_date_str,
        "subtotal": float(revision.subtotal),
        "discount_amount": float(revision.discount_amount),
        "tax_rate": float(revision.tax_rate),
        "tax_amount": float(revision.tax_amount),
        "grand_total": float(revision.grand_total),
        "agent_name": quotation.agent.full_name if quotation.agent else "Livguard Sales Team",
        "agent_mobile": quotation.agent.mobile if quotation.agent and quotation.agent.mobile else None,
        "items": items_data,
        "pdf_download_url": pdf_download_url
    }

@router.get("/q/{quotation_number}/{short_code}/pdf")
@limiter.limit("60/minute")
async def download_public_quotation_pdf_short(
    quotation_number: str,
    short_code: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Public customer endpoint to stream or download PDF using short code link /q/{quotation_number}/{short_code}.
    """
    return await download_public_quotation_pdf(
        token=short_code,
        request=request,
        quotation_number=quotation_number,
        db=db
    )

@router.get("/{quotation_number}/{token}/pdf")
@limiter.limit("60/minute")
async def download_public_quotation_pdf_with_number(
    quotation_number: str,
    token: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Public customer endpoint to stream or download the exact immutable quotation PDF
    with strict quotation number matching.
    """
    return await download_public_quotation_pdf(
        token=token,
        request=request,
        quotation_number=quotation_number,
        db=db
    )

@router.get("/{token}/pdf")
@limiter.limit("60/minute")
async def download_public_quotation_pdf(
    token: str,
    request: Request,
    quotation_number: str | None = None,
    db: Session = Depends(get_db)
):
    """
    Public customer endpoint to stream or download the exact immutable quotation PDF.
    """
    link = get_link_by_token(token, db)
    validate_quotation_number_match(link, quotation_number)
    record_access_event(link, ShareAccessEventType.DOWNLOAD.value, request, db)

    quotation = link.quotation
    revision = link.revision

    # Retrieve or generate the immutable PDF artifact
    artifact, pdf_bytes, _ = await QuotationArtifactService.get_or_create_artifact(
        db=db,
        quotation=quotation,
        revision=revision
    )

    clean_num = re.sub(r"[^a-zA-Z0-9_-]", "_", quotation.quotation_number or "quotation")
    filename = f"Livguard_Quotation_{clean_num}_Rev{revision.revision_number}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-store, no-cache, must-revalidate, private",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )

@router.get("/q/{quotation_number}/{short_code}")
@limiter.limit("60/minute")
def get_public_quotation_details_short(
    quotation_number: str,
    short_code: str,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Public customer endpoint to fetch metadata using short code link /q/{quotation_number}/{short_code}.
    """
    return get_public_quotation_details(
        token=short_code,
        request=request,
        response=response,
        quotation_number=quotation_number,
        db=db
    )

@router.get("/{quotation_number}/{token}")
@limiter.limit("60/minute")
def get_public_quotation_details_with_number(
    quotation_number: str,
    token: str,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Public customer endpoint to fetch metadata with quotation number verification.
    """
    return get_public_quotation_details(
        token=token,
        request=request,
        response=response,
        quotation_number=quotation_number,
        db=db
    )
