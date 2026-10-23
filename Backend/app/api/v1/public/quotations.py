import hashlib
import json
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

def get_link_by_token(token: str, db: Session) -> QuotationShareLink:
    if not token or len(token.strip()) < 16:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quotation link is invalid or has been revoked."
        )

    token_hash = hashlib.sha256(token.strip().encode("utf-8")).hexdigest()
    link = db.query(QuotationShareLink).filter(
        QuotationShareLink.token_hash == token_hash
    ).first()

    if not link or link.is_revoked:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Quotation link is invalid or has been revoked."
        )

    return link

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
        "pdf_download_url": f"/api/v1/public/quotations/{token}/pdf"
    }

@router.get("/{token}/pdf")
@limiter.limit("60/minute")
async def download_public_quotation_pdf(
    token: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Public customer endpoint to stream or download the exact immutable quotation PDF.
    """
    link = get_link_by_token(token, db)
    record_access_event(link, ShareAccessEventType.DOWNLOAD.value, request, db)

    quotation = link.quotation
    revision = link.revision

    # Retrieve or generate the immutable PDF artifact
    artifact, pdf_bytes, _ = await QuotationArtifactService.get_or_create_artifact(
        db=db,
        quotation=quotation,
        revision=revision
    )

    clean_num = (quotation.quotation_number or "quotation").replace("/", "_")
    filename = f"Livguard_Quotation_{clean_num}_Rev{revision.revision_number}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-store, no-cache, must-revalidate, private",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )
