from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import logging
import secrets
import hashlib

from app.core.database import get_db
from app.core.dependencies import require_agent, log_audit_event
from app.models.base import utc_now
from app.models.user import User, UserRole
from app.models.quotation import Quotation, QuotationRevision, QuotationItem, QuotationStatus
from app.models.coupon import CouponRedemption
from app.models.settings import CompanySettings, TaxSettings
from app.models.sharing import QuotationShareLink, SharedQuotationAccessLog
from app.schemas.quotation import QuotationCreateRequest, QuotationPreviewRequest, QuotationPreviewResponse
from app.services.pricing_service import PricingService
from app.services.numbering_service import NumberingService
from app.services.document_service import DocumentService
from app.services.customer_service import CustomerService
from app.services.quotation_artifact_service import QuotationArtifactService

router = APIRouter(prefix="/agent/quotations", tags=["Agent Quotations"])

@router.post("/preview", response_model=QuotationPreviewResponse)
def preview_quotation(
    quote_in: QuotationPreviewRequest,
    current_agent: User = Depends(require_agent),
    db: Session = Depends(get_db)
):
    try:
        calc_result = PricingService.calculate_quotation(
            db=db,
            items_input=quote_in.items,
            coupon_code=quote_in.coupon_code,
            agent_id=current_agent.id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return QuotationPreviewResponse(
        customer_name=quote_in.customer_name or "Customer Preview",
        customer_mobile=quote_in.customer_mobile or "9876543210",
        items=calc_result["items"],
        subtotal=calc_result["subtotal"],
        discount_amount=calc_result["discount_amount"],
        coupon_code=calc_result["coupon_code"],
        tax_rate=calc_result["tax_rate"],
        tax_amount=calc_result["tax_amount"],
        grand_total=calc_result["grand_total"]
    )

@router.post("/draft")
def save_draft_quotation(
    quote_in: QuotationCreateRequest,
    request: Request,
    current_agent: User = Depends(require_agent),
    db: Session = Depends(get_db)
):
    try:
        calc_result = PricingService.calculate_quotation(
            db=db,
            items_input=quote_in.items,
            coupon_code=quote_in.coupon_code,
            agent_id=current_agent.id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Normalize and get or create canonical customer
    try:
        customer = CustomerService.get_or_create_customer(
            db=db,
            name=quote_in.customer_name,
            raw_mobile=quote_in.customer_mobile,
            email=quote_in.customer_email,
            address=quote_in.customer_address,
            agent_id=current_agent.id
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    quotation = Quotation(
        quotation_number=None, # No issued number for drafts
        current_revision_number=0,
        agent_id=current_agent.id,
        customer_id=customer.id,
        source_quotation_id=quote_in.source_quotation_id,
        customer_name=quote_in.customer_name,
        customer_mobile=customer.normalized_mobile,
        customer_email=quote_in.customer_email,
        customer_address=quote_in.customer_address,
        status=QuotationStatus.DRAFT
    )
    db.add(quotation)
    db.flush()

    rev = QuotationRevision(
        quotation_id=quotation.id,
        revision_number=0,
        revision_label="Draft",
        subtotal=calc_result["subtotal"],
        discount_amount=calc_result["discount_amount"],
        coupon_id=calc_result["coupon"].id if calc_result["coupon"] else None,
        coupon_code=calc_result["coupon_code"],
        tax_rate=calc_result["tax_rate"],
        tax_amount=calc_result["tax_amount"],
        grand_total=calc_result["grand_total"],
        is_superseded=False,
        created_by_id=current_agent.id
    )
    db.add(rev)
    db.flush()

    for itm in calc_result["items"]:
        item_rec = QuotationItem(
            revision_id=rev.id,
            product_id=itm["product_id"],
            sku=itm["sku"],
            product_name=itm["product_name"],
            description=itm["description"],
            image_url=itm.get("image_url"),
            unit_price=itm["unit_price"],
            quantity=itm["quantity"],
            total_price=itm["total_price"]
        )
        db.add(item_rec)

    db.commit()
    log_audit_event(db, current_agent, "SAVE_DRAFT_QUOTATION", "Quotation", quotation.id, {}, request)
    return {"message": "Draft quotation saved", "quotation_id": quotation.id}

@router.post("/issue")
def issue_new_quotation(
    quote_in: QuotationCreateRequest,
    request: Request,
    current_agent: User = Depends(require_agent),
    db: Session = Depends(get_db)
):
    try:
        calc_result = PricingService.calculate_quotation(
            db=db,
            items_input=quote_in.items,
            coupon_code=quote_in.coupon_code,
            agent_id=current_agent.id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    company_settings = db.query(CompanySettings).order_by(CompanySettings.version.desc()).first()
    tax_settings = db.query(TaxSettings).order_by(TaxSettings.version.desc()).first()

    # Generate sequential unique quotation number
    quote_number = NumberingService.generate_quotation_number(db)

    # Normalize and get or create canonical customer
    try:
        customer = CustomerService.get_or_create_customer(
            db=db,
            name=quote_in.customer_name,
            raw_mobile=quote_in.customer_mobile,
            email=quote_in.customer_email,
            address=quote_in.customer_address,
            agent_id=current_agent.id
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    quotation = Quotation(
        quotation_number=quote_number,
        current_revision_number=0,
        agent_id=current_agent.id,
        customer_id=customer.id,
        source_quotation_id=quote_in.source_quotation_id,
        customer_name=quote_in.customer_name,
        customer_mobile=customer.normalized_mobile,
        customer_email=quote_in.customer_email,
        customer_address=quote_in.customer_address,
        status=QuotationStatus.ISSUED
    )
    db.add(quotation)
    db.flush()

    # Create immutable Revision 0 snapshot
    company_snap = {
        "company_name": company_settings.company_name if company_settings else "Livguard",
        "phone": company_settings.phone if company_settings else "",
        "terms": company_settings.terms_conditions if company_settings else "",
        "address": company_settings.address if company_settings else "",
        "email": company_settings.email if company_settings else "",
        "website": company_settings.website if company_settings else "",
        "quotation_validity_days": company_settings.quotation_validity_days if company_settings else 15
    }
    tax_snap = {
        "rate": float(calc_result["tax_rate"]),
        "policy": calc_result["tax_policy"]
    }

    rev = QuotationRevision(
        quotation_id=quotation.id,
        revision_number=0,
        revision_label="Original",
        subtotal=calc_result["subtotal"],
        discount_amount=calc_result["discount_amount"],
        coupon_id=calc_result["coupon"].id if calc_result["coupon"] else None,
        coupon_code=calc_result["coupon_code"],
        tax_rate=calc_result["tax_rate"],
        tax_amount=calc_result["tax_amount"],
        grand_total=calc_result["grand_total"],
        company_snapshot=json.dumps(company_snap),
        tax_snapshot=json.dumps(tax_snap),
        is_superseded=False,
        created_by_id=current_agent.id
    )
    db.add(rev)
    db.flush()

    for itm in calc_result["items"]:
        item_rec = QuotationItem(
            revision_id=rev.id,
            product_id=itm["product_id"],
            sku=itm["sku"],
            product_name=itm["product_name"],
            description=itm["description"],
            image_url=itm.get("image_url"),
            unit_price=itm["unit_price"],
            quantity=itm["quantity"],
            total_price=itm["total_price"]
        )
        db.add(item_rec)

    # Record coupon redemption if applied
    if calc_result["coupon"]:
        coupon = calc_result["coupon"]
        coupon.used_count += 1
        db.add(CouponRedemption(
            coupon_id=coupon.id,
            quotation_id=quotation.id,
            agent_id=current_agent.id,
            discount_granted=calc_result["discount_amount"]
        ))

    db.commit()
    log_audit_event(db, current_agent, "ISSUE_QUOTATION", "Quotation", quotation.id, {"quotation_number": quote_number}, request)
    return {"message": "Quotation issued successfully", "quotation_id": quotation.id, "quotation_number": quote_number}

@router.post("/{quotation_id}/issue-draft")
def issue_draft_quotation(
    quotation_id: str,
    request: Request,
    current_agent: User = Depends(require_agent),
    db: Session = Depends(get_db)
):
    quotation = db.query(Quotation).filter(
        Quotation.id == quotation_id,
        Quotation.agent_id == current_agent.id
    ).first()
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    if quotation.status != QuotationStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Only DRAFT quotations can be issued.")

    quote_number = NumberingService.generate_quotation_number(db)
    quotation.quotation_number = quote_number
    quotation.status = QuotationStatus.ISSUED
    quotation.updated_at = datetime.utcnow()

    # Update revision 0
    if quotation.revisions:
        rev = quotation.revisions[0]
        rev.revision_label = "Original"

    db.commit()
    log_audit_event(db, current_agent, "ISSUE_QUOTATION", "Quotation", quotation.id, {"quotation_number": quote_number, "from_draft": True}, request)
    return {"message": "Quotation officially issued", "quotation_id": quotation.id, "quotation_number": quote_number}

@router.get("")
def list_my_quotations(
    status_filter: Optional[QuotationStatus] = None,
    current_agent: User = Depends(require_agent),
    db: Session = Depends(get_db)
):
    query = db.query(Quotation).filter(Quotation.agent_id == current_agent.id)
    if status_filter:
        query = query.filter(Quotation.status == status_filter)

    quotations = query.order_by(Quotation.created_at.desc()).all()
    results = []
    for q in quotations:
        latest_rev = q.revisions[0] if q.revisions else None
        results.append({
            "id": q.id,
            "quotation_number": q.quotation_number or "DRAFT",
            "current_revision_number": q.current_revision_number,
            "customer_name": q.customer_name,
            "customer_mobile": q.customer_mobile,
            "status": q.status,
            "grand_total": float(latest_rev.grand_total) if latest_rev else 0.0,
            "revision_count": len(q.revisions),
            "created_at": q.created_at
        })
    return results

@router.get("/{quotation_id}")
def get_my_quotation_details(
    quotation_id: str,
    current_agent: User = Depends(require_agent),
    db: Session = Depends(get_db)
):
    quotation = db.query(Quotation).filter(Quotation.id == quotation_id).first()
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    # Strictly prevent unauthorized access to other agents' quotations
    if quotation.agent_id != current_agent.id and current_agent.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Access forbidden: This quotation belongs to another agent.")

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
        "quotation_number": quotation.quotation_number or "DRAFT",
        "current_revision_number": quotation.current_revision_number,
        "customer_name": quotation.customer_name,
        "customer_mobile": quotation.customer_mobile,
        "customer_email": quotation.customer_email,
        "customer_address": quotation.customer_address,
        "status": quotation.status,
        "created_at": quotation.created_at,
        "revisions": revisions_data
    }

@router.post("/{quotation_id}/revise")
def revise_quotation(
    quotation_id: str,
    quote_in: QuotationCreateRequest,
    request: Request,
    current_agent: User = Depends(require_agent),
    db: Session = Depends(get_db)
):
    quotation = db.query(Quotation).filter(Quotation.id == quotation_id).first()
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    if quotation.agent_id != current_agent.id and current_agent.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Access forbidden.")

    # Business Rule: If payment reported (pending/verified) or order confirmed -> FREEZE
    if quotation.status in [QuotationStatus.PAYMENT_PENDING, QuotationStatus.PAYMENT_VERIFIED]:
        raise HTTPException(
            status_code=400,
            detail="Cannot revise quotation while payment is under review or verified. Contact Admin to resolve."
        )
    if quotation.status == QuotationStatus.ORDER_CONFIRMED:
        raise HTTPException(
            status_code=400,
            detail="Order has been confirmed. Confirmed quotations are permanently locked."
        )
    if quotation.status == QuotationStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Cannot revise a cancelled quotation.")

    # Server-side recalculation using current authorized product prices & tax rules
    try:
        calc_result = PricingService.calculate_quotation(
            db=db,
            items_input=quote_in.items,
            coupon_code=quote_in.coupon_code,
            agent_id=current_agent.id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Mark all previous revisions as superseded
    for rev in quotation.revisions:
        rev.is_superseded = True

    new_rev_number = quotation.current_revision_number + 1
    new_rev_label = f"Revision {new_rev_number}"

    company_settings = db.query(CompanySettings).order_by(CompanySettings.version.desc()).first()
    company_snap = {
        "company_name": company_settings.company_name if company_settings else "Livguard",
        "phone": company_settings.phone if company_settings else "",
        "terms": company_settings.terms_conditions if company_settings else "",
        "address": company_settings.address if company_settings else "",
        "email": company_settings.email if company_settings else "",
        "website": company_settings.website if company_settings else "",
        "quotation_validity_days": company_settings.quotation_validity_days if company_settings else 15
    }
    tax_snap = {
        "rate": float(calc_result["tax_rate"]),
        "policy": calc_result["tax_policy"]
    }

    new_rev = QuotationRevision(
        quotation_id=quotation.id,
        revision_number=new_rev_number,
        revision_label=new_rev_label,
        subtotal=calc_result["subtotal"],
        discount_amount=calc_result["discount_amount"],
        coupon_id=calc_result["coupon"].id if calc_result["coupon"] else None,
        coupon_code=calc_result["coupon_code"],
        tax_rate=calc_result["tax_rate"],
        tax_amount=calc_result["tax_amount"],
        grand_total=calc_result["grand_total"],
        company_snapshot=json.dumps(company_snap),
        tax_snapshot=json.dumps(tax_snap),
        is_superseded=False,
        created_by_id=current_agent.id
    )
    db.add(new_rev)
    db.flush()

    for itm in calc_result["items"]:
        db.add(QuotationItem(
            revision_id=new_rev.id,
            product_id=itm["product_id"],
            sku=itm["sku"],
            product_name=itm["product_name"],
            description=itm["description"],
            image_url=itm.get("image_url"),
            unit_price=itm["unit_price"],
            quantity=itm["quantity"],
            total_price=itm["total_price"]
        ))

    quotation.current_revision_number = new_rev_number
    # Update customer info if modified
    quotation.customer_name = quote_in.customer_name
    quotation.customer_mobile = quote_in.customer_mobile
    if quote_in.customer_email: quotation.customer_email = quote_in.customer_email
    if quote_in.customer_address: quotation.customer_address = quote_in.customer_address

    db.commit()
    log_audit_event(db, current_agent, "CREATE_REVISION", "Quotation", quotation.id, {"revision": new_rev_number}, request)
    return {"message": f"Successfully created {new_rev_label}", "revision_number": new_rev_number}

@router.post("/{quotation_id}/duplicate")
def duplicate_quotation(
    quotation_id: str,
    request: Request,
    current_agent: User = Depends(require_agent),
    db: Session = Depends(get_db)
):
    original = db.query(Quotation).filter(Quotation.id == quotation_id).first()
    if not original:
        raise HTTPException(status_code=404, detail="Quotation not found")
    if original.agent_id != current_agent.id and current_agent.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Access forbidden.")

    latest_rev = original.revisions[0]

    # Create new draft
    new_quote = Quotation(
        quotation_number=None,
        current_revision_number=0,
        agent_id=current_agent.id,
        customer_name=original.customer_name,
        customer_mobile=original.customer_mobile,
        customer_email=original.customer_email,
        customer_address=original.customer_address,
        status=QuotationStatus.DRAFT
    )
    db.add(new_quote)
    db.flush()

    new_rev = QuotationRevision(
        quotation_id=new_quote.id,
        revision_number=0,
        revision_label="Draft",
        subtotal=latest_rev.subtotal,
        discount_amount=Decimal("0.00"),
        coupon_id=None,
        coupon_code=None,
        tax_rate=latest_rev.tax_rate,
        tax_amount=latest_rev.tax_amount,
        grand_total=latest_rev.grand_total,
        is_superseded=False,
        created_by_id=current_agent.id
    )
    db.add(new_rev)
    db.flush()

    for item in latest_rev.items:
        db.add(QuotationItem(
            revision_id=new_rev.id,
            product_id=item.product_id,
            sku=item.sku,
            product_name=item.product_name,
            description=item.description,
            image_url=item.image_url,
            unit_price=item.unit_price,
            quantity=item.quantity,
            total_price=item.total_price
        ))

    db.commit()
    log_audit_event(db, current_agent, "DUPLICATE_QUOTATION", "Quotation", new_quote.id, {"original_id": original.id}, request)
    return {"message": "Quotation duplicated as new draft", "quotation_id": new_quote.id}

@router.get("/{quotation_id}/revisions/{revision_id}/pdf")
async def download_my_quotation_pdf(
    quotation_id: str,
    revision_id: str,
    current_agent: User = Depends(require_agent),
    db: Session = Depends(get_db)
):
    quotation = db.query(Quotation).filter(Quotation.id == quotation_id).first()
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    if quotation.agent_id != current_agent.id and current_agent.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Access forbidden.")

    revision = db.query(QuotationRevision).filter(QuotationRevision.id == revision_id, QuotationRevision.quotation_id == quotation.id).first()
    if not revision:
        raise HTTPException(status_code=404, detail="Revision not found")

    try:
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
    except Exception as e:
        logging.error(f"Error generating PDF for quotation {quotation_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate quotation PDF. Please check server logs.")

@router.get("/{quotation_id}/revisions/{revision_id}/png")
async def download_my_quotation_png(
    quotation_id: str,
    revision_id: str,
    current_agent: User = Depends(require_agent),
    db: Session = Depends(get_db)
):
    quotation = db.query(Quotation).filter(Quotation.id == quotation_id).first()
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    if quotation.agent_id != current_agent.id and current_agent.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Access forbidden.")

    revision = db.query(QuotationRevision).filter(QuotationRevision.id == revision_id, QuotationRevision.quotation_id == quotation.id).first()
    if not revision:
        raise HTTPException(status_code=404, detail="Revision not found")

    try:
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
    except Exception as e:
        logging.error(f"Error generating PNG for quotation {quotation_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate quotation image. Please check server logs.")

@router.post("/{quotation_id}/reuse")
def reuse_quotation(
    quotation_id: str,
    request: Request,
    current_agent: User = Depends(require_agent),
    db: Session = Depends(get_db)
):
    """
    Creates a new draft quotation based on a historical quotation.
    Revalidates prices, coupons, and tax settings on the backend.
    """
    return CustomerService.reuse_quotation(
        db=db,
        source_quotation_id=quotation_id,
        current_agent=current_agent,
        request=request
    )

@router.post("/{quotation_id}/revisions/{revision_id}/share")
async def create_or_reuse_share_link(
    quotation_id: str,
    revision_id: str,
    request: Request,
    regenerate: bool = False,
    current_agent: User = Depends(require_agent),
    db: Session = Depends(get_db)
):
    """
    Creates or regenerates a cryptographically unguessable public sharing link for an issued quotation revision.
    Guarantees that an immutable PDF artifact exists prior to sharing.
    If an active link already exists and regenerate=False, returns active link metadata without generating broken URLs.
    """
    quotation = db.query(Quotation).filter(Quotation.id == quotation_id).first()
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    if quotation.agent_id != current_agent.id and current_agent.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Access forbidden: This quotation belongs to another agent.")

    if quotation.status == QuotationStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Cannot share a draft quotation. The quotation must be issued first.")

    revision = db.query(QuotationRevision).filter(
        QuotationRevision.id == revision_id,
        QuotationRevision.quotation_id == quotation.id
    ).first()
    if not revision:
        raise HTTPException(status_code=404, detail="Revision not found for this quotation")

    # 1. Ensure immutable PDF artifact is sealed in storage
    try:
        await QuotationArtifactService.get_or_create_artifact(db, quotation, revision)
    except Exception as e:
        logging.error(f"Failed to seal PDF artifact for quotation {quotation_id} rev {revision_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to seal quotation artifact. Sharing link cannot be created.")

    # 2. Check for existing active link
    active_link = db.query(QuotationShareLink).filter(
        QuotationShareLink.revision_id == revision.id,
        QuotationShareLink.is_revoked == False
    ).first()

    if active_link and not regenerate:
        return {
            "is_new": False,
            "active_link_exists": True,
            "share_link_id": active_link.id,
            "revision_id": revision.id,
            "revision_number": revision.revision_number,
            "created_at": active_link.created_at,
            "message": "An active share link already exists for this revision. You can regenerate a new link if needed."
        }

    # If regenerate=True, revoke previous link
    if active_link and regenerate:
        active_link.is_revoked = True
        active_link.revoked_at = utc_now()
        active_link.revoked_by_id = current_agent.id

    # 3. Generate 256-bit cryptographic unguessable raw token
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    new_link = QuotationShareLink(
        quotation_id=quotation.id,
        revision_id=revision.id,
        token_hash=token_hash,
        created_by_id=current_agent.id,
        is_revoked=False
    )
    db.add(new_link)
    db.commit()
    db.refresh(new_link)

    log_audit_event(
        db,
        current_agent,
        "CREATE_SHARE_LINK",
        "QuotationShareLink",
        new_link.id,
        {"quotation_id": quotation.id, "revision_id": revision.id, "regenerated": bool(active_link)},
        request
    )

    return {
        "is_new": True,
        "active_link_exists": False,
        "share_link_id": new_link.id,
        "revision_id": revision.id,
        "revision_number": revision.revision_number,
        "raw_token": raw_token,
        "share_url": f"/shared/{raw_token}",
        "created_at": new_link.created_at
    }

@router.get("/{quotation_id}/share-links")
def list_quotation_share_links(
    quotation_id: str,
    current_agent: User = Depends(require_agent),
    db: Session = Depends(get_db)
):
    """
    Returns the history of all sharing links created for revisions of this quotation,
    including active/revoked status, creation date, and view/download counts.
    """
    quotation = db.query(Quotation).filter(Quotation.id == quotation_id).first()
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    if quotation.agent_id != current_agent.id and current_agent.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Access forbidden: This quotation belongs to another agent.")

    links = db.query(QuotationShareLink).filter(
        QuotationShareLink.quotation_id == quotation_id
    ).order_by(QuotationShareLink.created_at.desc()).all()

    results = []
    for l in links:
        view_count = sum(1 for log in l.access_logs if log.event_type == "VIEW")
        download_count = sum(1 for log in l.access_logs if log.event_type == "DOWNLOAD")
        results.append({
            "id": l.id,
            "revision_id": l.revision_id,
            "revision_number": l.revision.revision_number if l.revision else 0,
            "revision_label": l.revision.revision_label if l.revision else "Revision",
            "is_revoked": l.is_revoked,
            "created_at": l.created_at,
            "revoked_at": l.revoked_at,
            "last_accessed_at": l.last_accessed_at,
            "view_count": view_count,
            "download_count": download_count
        })

    return results

@router.post("/{quotation_id}/share-links/{link_id}/revoke")
def revoke_quotation_share_link(
    quotation_id: str,
    link_id: str,
    request: Request,
    current_agent: User = Depends(require_agent),
    db: Session = Depends(get_db)
):
    """
    Immediately revokes an active sharing link. Once revoked, any subsequent public access is denied.
    """
    quotation = db.query(Quotation).filter(Quotation.id == quotation_id).first()
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    if quotation.agent_id != current_agent.id and current_agent.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Access forbidden: This quotation belongs to another agent.")

    link = db.query(QuotationShareLink).filter(
        QuotationShareLink.id == link_id,
        QuotationShareLink.quotation_id == quotation.id
    ).first()
    if not link:
        raise HTTPException(status_code=404, detail="Share link not found")

    if link.is_revoked:
        return {"message": "Share link is already revoked", "share_link_id": link.id}

    link.is_revoked = True
    link.revoked_at = utc_now()
    link.revoked_by_id = current_agent.id
    db.commit()

    log_audit_event(
        db,
        current_agent,
        "REVOKE_SHARE_LINK",
        "QuotationShareLink",
        link.id,
        {"quotation_id": quotation.id, "revision_id": link.revision_id},
        request
    )

    return {
        "message": "Share link revoked successfully. Public access has been disabled.",
        "share_link_id": link.id
    }

