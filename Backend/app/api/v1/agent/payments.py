from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
from decimal import Decimal

from app.core.database import get_db
from app.core.dependencies import require_agent, log_audit_event
from app.models.user import User, UserRole
from app.models.quotation import Quotation, QuotationStatus
from app.models.payment import Payment, PaymentStatus
from app.schemas.payment import PaymentReportRequest, PaymentResponse

router = APIRouter(prefix="/agent/payments", tags=["Agent Payment Reporting"])

@router.post("/report", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def report_payment(
    report_in: PaymentReportRequest,
    request: Request,
    current_agent: User = Depends(require_agent),
    db: Session = Depends(get_db)
):
    quotation = db.query(Quotation).filter(Quotation.id == report_in.quotation_id).first()
    if not quotation:
        raise HTTPException(status_code=404, detail="Quotation not found")

    if quotation.agent_id != current_agent.id and current_agent.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Access forbidden: Quotation belongs to another agent.")

    if quotation.status == QuotationStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Cannot report payment for a draft quotation. The quotation must be issued first.")

    if quotation.status in [QuotationStatus.PAYMENT_PENDING, QuotationStatus.PAYMENT_VERIFIED]:
        raise HTTPException(status_code=400, detail="A payment report has already been submitted for this quotation.")

    if quotation.status == QuotationStatus.ORDER_CONFIRMED:
        raise HTTPException(status_code=400, detail="Order has already been confirmed for this quotation.")

    # Check that transaction_ref is unique
    existing_ref = db.query(Payment).filter(Payment.transaction_ref == report_in.transaction_ref.strip()).first()
    if existing_ref:
        raise HTTPException(status_code=400, detail=f"Transaction reference '{report_in.transaction_ref}' has already been reported.")

    latest_revision = quotation.revisions[0]
    expected_amount = latest_revision.grand_total

    # Business Rule: Initial workflow requires payment of the full final quotation amount
    if Decimal(str(report_in.amount)) != Decimal(str(expected_amount)):
        raise HTTPException(
            status_code=400,
            detail=f"Reported payment amount (₹{report_in.amount}) must match the full quotation grand total (₹{expected_amount})."
        )

    new_payment = Payment(
        quotation_id=quotation.id,
        revision_id=latest_revision.id,
        reported_by_id=current_agent.id,
        amount=report_in.amount,
        payment_date=report_in.payment_date or datetime.now(timezone.utc),
        payment_method=report_in.payment_method,
        transaction_ref=report_in.transaction_ref.strip(),
        evidence_url=report_in.evidence_url,
        remarks=report_in.remarks,
        status=PaymentStatus.PENDING_REVIEW
    )
    db.add(new_payment)

    # Freeze quotation for editing
    quotation.status = QuotationStatus.PAYMENT_PENDING
    db.commit()
    db.refresh(new_payment)

    log_audit_event(db, current_agent, "REPORT_PAYMENT", "Payment", new_payment.id, {"quotation_id": quotation.id, "amount": str(new_payment.amount)}, request)

    return PaymentResponse(
        id=new_payment.id,
        quotation_id=new_payment.quotation_id,
        quotation_number=quotation.quotation_number,
        revision_id=new_payment.revision_id,
        reported_by_id=new_payment.reported_by_id,
        reported_by_name=current_agent.full_name,
        amount=new_payment.amount,
        payment_date=new_payment.payment_date,
        payment_method=new_payment.payment_method,
        transaction_ref=new_payment.transaction_ref,
        evidence_url=new_payment.evidence_url,
        status=new_payment.status,
        remarks=new_payment.remarks,
        created_at=new_payment.created_at
    )

@router.get("/my-reports", response_model=List[PaymentResponse])
def get_my_payment_reports(
    current_agent: User = Depends(require_agent),
    db: Session = Depends(get_db)
):
    payments = db.query(Payment).filter(Payment.reported_by_id == current_agent.id).order_by(Payment.created_at.desc()).all()
    results = []
    for p in payments:
        results.append(PaymentResponse(
            id=p.id,
            quotation_id=p.quotation_id,
            quotation_number=p.quotation.quotation_number if p.quotation else None,
            revision_id=p.revision_id,
            reported_by_id=p.reported_by_id,
            reported_by_name=current_agent.full_name,
            amount=p.amount,
            payment_date=p.payment_date,
            payment_method=p.payment_method,
            transaction_ref=p.transaction_ref,
            evidence_url=p.evidence_url,
            status=p.status,
            rejection_reason=p.rejection_reason,
            verified_by_id=p.verified_by_id,
            verified_by_name=p.verified_by.full_name if p.verified_by else None,
            verified_at=p.verified_at,
            remarks=p.remarks,
            created_at=p.created_at
        ))
    return results
