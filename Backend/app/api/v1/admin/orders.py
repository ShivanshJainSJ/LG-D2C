from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.dependencies import require_admin, log_audit_event
from app.models.user import User
from app.models.quotation import Quotation, QuotationStatus
from app.models.payment import Payment, PaymentStatus
from app.models.order import Order, OrderStatus
from app.models.settings import CompanySettings
from app.schemas.order import OrderCreateRequest, OrderResponse
from app.services.numbering_service import NumberingService
from app.services.document_service import DocumentService

router = APIRouter(prefix="/admin/orders", tags=["Admin Order Confirmation"])

@router.get("", response_model=List[OrderResponse])
def list_orders(
    status_filter: Optional[OrderStatus] = None,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    query = db.query(Order)
    if status_filter:
        query = query.filter(Order.status == status_filter)

    orders = query.order_by(Order.created_at.desc()).all()
    results = []
    for o in orders:
        results.append(OrderResponse(
            id=o.id,
            order_number=o.order_number,
            quotation_id=o.quotation_id,
            quotation_number=o.quotation.quotation_number if o.quotation else "N/A",
            payment_id=o.payment_id,
            confirmed_by_id=o.confirmed_by_id,
            confirmed_by_name=o.confirmed_by.full_name if o.confirmed_by else "Admin",
            confirmed_amount=o.confirmed_amount,
            order_date=o.order_date,
            expected_delivery_date=o.expected_delivery_date,
            remarks=o.remarks,
            status=o.status,
            created_at=o.created_at
        ))
    return results

@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def confirm_order(
    order_in: OrderCreateRequest,
    request: Request,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    quotation = db.query(Quotation).filter(Quotation.id == order_in.quotation_id).first()
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")

    if quotation.status != QuotationStatus.PAYMENT_VERIFIED:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot confirm order. Quotation status is '{quotation.status.value}', but must be 'PAYMENT_VERIFIED'."
        )

    # Check for verified payment
    verified_payment = db.query(Payment).filter(
        Payment.quotation_id == quotation.id,
        Payment.status == PaymentStatus.VERIFIED
    ).first()
    if not verified_payment:
        raise HTTPException(status_code=400, detail="No verified payment found for this quotation.")

    # Check if order already exists
    existing_order = db.query(Order).filter(Order.quotation_id == quotation.id).first()
    if existing_order:
        raise HTTPException(status_code=400, detail=f"Order has already been confirmed with number: {existing_order.order_number}")

    # Generate sequential unique order number
    order_number = NumberingService.generate_order_number(db)
    latest_revision = quotation.revisions[0]

    new_order = Order(
        order_number=order_number,
        quotation_id=quotation.id,
        revision_id=latest_revision.id,
        payment_id=verified_payment.id,
        confirmed_by_id=current_admin.id,
        confirmed_amount=latest_revision.grand_total,
        expected_delivery_date=order_in.expected_delivery_date,
        remarks=order_in.remarks,
        status=OrderStatus.CONFIRMED
    )
    db.add(new_order)

    # Lock quotation status permanently
    quotation.status = QuotationStatus.ORDER_CONFIRMED
    db.commit()
    db.refresh(new_order)

    log_audit_event(db, current_admin, "CONFIRM_ORDER", "Order", new_order.id, {"order_number": order_number, "quotation_id": quotation.id}, request)

    return OrderResponse(
        id=new_order.id,
        order_number=new_order.order_number,
        quotation_id=new_order.quotation_id,
        quotation_number=quotation.quotation_number,
        payment_id=new_order.payment_id,
        confirmed_by_id=new_order.confirmed_by_id,
        confirmed_by_name=current_admin.full_name,
        confirmed_amount=new_order.confirmed_amount,
        order_date=new_order.order_date,
        expected_delivery_date=new_order.expected_delivery_date,
        remarks=new_order.remarks,
        status=new_order.status,
        created_at=new_order.created_at
    )

@router.get("/{order_id}/pdf")
async def download_order_pdf(
    order_id: str,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    company_settings = db.query(CompanySettings).order_by(CompanySettings.version.desc()).first()
    html_content = DocumentService.render_order_html(order, company_settings)
    pdf_bytes = await DocumentService.generate_pdf_from_html(html_content)

    clean_num = order.order_number.replace("/", "_")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Livguard_Order_{clean_num}.pdf"}
    )

@router.get("/{order_id}/png")
async def download_order_png(
    order_id: str,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    company_settings = db.query(CompanySettings).order_by(CompanySettings.version.desc()).first()
    html_content = DocumentService.render_order_html(order, company_settings)
    png_bytes = await DocumentService.generate_png_from_html(html_content)

    clean_num = order.order_number.replace("/", "_")
    return Response(
        content=png_bytes,
        media_type="image/png",
        headers={"Content-Disposition": f"attachment; filename=Livguard_Order_{clean_num}.png"}
    )
