from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.core.config import settings
from app.core.dependencies import require_admin, log_audit_event
from app.models.user import User
from app.models.quotation import Quotation, QuotationRevision, QuotationItem, QuotationStatus
from app.models.settings import CompanySettings
from app.schemas.quotation import QuotationResponse, QuotationCancelRequest
from app.services.document_service import DocumentService
from app.services.quotation_artifact_service import QuotationArtifactService

router = APIRouter(prefix="/admin/quotations", tags=["Admin Quotation Management"])

@router.get("")
def list_all_quotations(
    search: Optional[str] = None,
    agent_id: Optional[str] = None,
    status_filter: Optional[QuotationStatus] = None,
    skip: int = 0,
    limit: int = 100,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    query = db.query(Quotation)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Quotation.quotation_number.ilike(search_term)) |
            (Quotation.customer_name.ilike(search_term)) |
            (Quotation.customer_mobile.ilike(search_term))
        )
    if agent_id:
        query = query.filter(Quotation.agent_id == agent_id)
    if status_filter:
        query = query.filter(Quotation.status == status_filter)

    total = query.count()
    quotations = query.order_by(Quotation.created_at.desc()).offset(skip).limit(limit).all()

    results = []
    for q in quotations:
        latest_rev = q.revisions[0] if q.revisions else None
        results.append({
            "id": q.id,
            "quotation_number": q.quotation_number,
            "current_revision_number": q.current_revision_number,
            "customer_name": q.customer_name,
            "customer_mobile": q.customer_mobile,
            "customer_email": q.customer_email,
            "agent_id": q.agent_id,
            "agent_name": q.agent.full_name if q.agent else "Unknown",
            "status": q.status,
            "grand_total": float(latest_rev.grand_total) if latest_rev else 0.0,
            "revision_count": len(q.revisions),
            "created_at": q.created_at,
            "updated_at": q.updated_at
        })

    return {"total": total, "items": results}

@router.get("/{quotation_id}")
def get_quotation_details(
    quotation_id: str,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    quotation = db.query(Quotation).filter(Quotation.id == quotation_id).first()
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")

    revisions_data = []
    for r in quotation.revisions:
        items_data = []
        for i in r.items:
            items_data.append({
                "id": i.id,
                "product_id": i.product_id,
                "sku": i.sku,
                "product_name": i.product_name,
                "description": i.description,
                "image_url": i.image_url or (i.product.image_url if i.product else None),
                "unit_price": float(i.unit_price),
                "quantity": i.quantity,
                "total_price": float(i.total_price)
            })
        revisions_data.append({
            "id": r.id,
            "revision_number": r.revision_number,
            "revision_label": r.revision_label,
            "subtotal": float(r.subtotal),
            "discount_amount": float(r.discount_amount),
            "coupon_code": r.coupon_code,
            "tax_rate": float(r.tax_rate),
            "tax_amount": float(r.tax_amount),
            "grand_total": float(r.grand_total),
            "is_superseded": r.is_superseded,
            "created_at": r.created_at,
            "items": items_data
        })

    return {
        "id": quotation.id,
        "quotation_number": quotation.quotation_number,
        "current_revision_number": quotation.current_revision_number,
        "customer_name": quotation.customer_name,
        "customer_mobile": quotation.customer_mobile,
        "customer_email": quotation.customer_email,
        "customer_address": quotation.customer_address,
        "agent_id": quotation.agent_id,
        "agent_name": quotation.agent.full_name if quotation.agent else "Unknown",
        "agent_mobile": quotation.agent.mobile if quotation.agent else None,
        "status": quotation.status,
        "cancellation_reason": quotation.cancellation_reason,
        "created_at": quotation.created_at,
        "revisions": revisions_data
    }

@router.post("/{quotation_id}/cancel")
def cancel_quotation(
    quotation_id: str,
    cancel_in: QuotationCancelRequest,
    request: Request,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    quotation = db.query(Quotation).filter(Quotation.id == quotation_id).first()
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")

    if quotation.status == QuotationStatus.ORDER_CONFIRMED:
        raise HTTPException(status_code=400, detail="Cannot cancel an order that has already been confirmed.")

    quotation.status = QuotationStatus.CANCELLED
    quotation.cancellation_reason = cancel_in.reason
    db.commit()

    log_audit_event(db, current_admin, "CANCEL_QUOTATION", "Quotation", quotation.id, {"reason": cancel_in.reason}, request)
    return {"message": "Quotation has been cancelled successfully"}

@router.get("/{quotation_id}/revisions/{revision_id}/pdf")
async def download_quotation_revision_pdf(
    quotation_id: str,
    revision_id: str,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    quotation = db.query(Quotation).filter(Quotation.id == quotation_id).first()
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    revision = db.query(QuotationRevision).filter(QuotationRevision.id == revision_id, QuotationRevision.quotation_id == quotation.id).first()
    if not revision:
        raise HTTPException(status_code=404, detail="Revision not found")

    company_settings = db.query(CompanySettings).order_by(CompanySettings.version.desc()).first()
    html_content = DocumentService.render_quotation_html(quotation, revision, company_settings)
    pdf_bytes = await DocumentService.generate_pdf_from_html(html_content)

    clean_num = (quotation.quotation_number or "draft").replace("/", "_")
    filename = f"Livguard_Quotation_{clean_num}_Rev{revision.revision_number}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/{quotation_id}/revisions/{revision_id}/png")
async def download_quotation_revision_png(
    quotation_id: str,
    revision_id: str,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    quotation = db.query(Quotation).filter(Quotation.id == quotation_id).first()
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    revision = db.query(QuotationRevision).filter(QuotationRevision.id == revision_id, QuotationRevision.quotation_id == quotation.id).first()
    if not revision:
        raise HTTPException(status_code=404, detail="Revision not found")

    company_settings = db.query(CompanySettings).order_by(CompanySettings.version.desc()).first()
    html_content = DocumentService.render_quotation_html(quotation, revision, company_settings)
    png_bytes = await DocumentService.generate_png_from_html(html_content)

    clean_num = (quotation.quotation_number or "draft").replace("/", "_")
    filename = f"Livguard_Quotation_{clean_num}_Rev{revision.revision_number}.png"
    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.post("/{quotation_id}/revisions/{revision_id}/repair-artifact")
async def repair_quotation_revision_artifact(
    quotation_id: str,
    revision_id: str,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Staging-only maintenance endpoint to regenerate a corrupted/broken quotation PDF artifact
    without creating a new revision or altering share links.
    Strictly forbidden in production.
    """
    env_lower = (settings.ENVIRONMENT or "").strip().lower()
    if env_lower == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Artifact repair is strictly forbidden in production. Please create a new quotation revision."
        )

    quotation = db.query(Quotation).filter(Quotation.id == quotation_id).first()
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    revision = db.query(QuotationRevision).filter(
        QuotationRevision.id == revision_id,
        QuotationRevision.quotation_id == quotation.id
    ).first()
    if not revision:
        raise HTTPException(status_code=404, detail="Revision not found")

    artifact, pdf_bytes, _ = await QuotationArtifactService.get_or_create_artifact(
        db=db,
        quotation=quotation,
        revision=revision,
        force_regenerate=True
    )
    return {
        "status": "repaired",
        "quotation_number": quotation.quotation_number,
        "revision_number": revision.revision_number,
        "byte_size": artifact.byte_size,
        "sha256_hash": artifact.sha256_hash
    }
