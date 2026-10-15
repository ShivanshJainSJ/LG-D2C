from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.dependencies import require_admin, log_audit_event
from app.models.user import User
from app.models.payment import Payment, PaymentStatus
from app.models.quotation import Quotation, QuotationStatus
from app.schemas.payment import PaymentVerifyRequest, PaymentResponse

router = APIRouter(prefix="/admin/payments", tags=["Admin Payment Verification"])

@router.get("", response_model=List[PaymentResponse])
def list_payments(
    status_filter: Optional[PaymentStatus] = None,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    query = db.query(Payment)
    if status_filter:
        query = query.filter(Payment.status == status_filter)

    payments = query.order_by(Payment.created_at.desc()).all()
    results = []
    for p in payments:
        results.append(PaymentResponse(
            id=p.id,
            quotation_id=p.quotation_id,
            quotation_number=p.quotation.quotation_number if p.quotation else None,
            revision_id=p.revision_id,
            reported_by_id=p.reported_by_id,
            reported_by_name=p.reported_by.full_name if p.reported_by else "Agent",
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

@router.put("/{payment_id}/verify")
def verify_or_reject_payment(
    payment_id: str,
    action_in: PaymentVerifyRequest,
    request: Request,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment record not found")

    if payment.status != PaymentStatus.PENDING_REVIEW:
        raise HTTPException(status_code=400, detail=f"Payment has already been processed with status: {payment.status.value}")

    quotation = db.query(Quotation).filter(Quotation.id == payment.quotation_id).first()
    if not quotation:
        raise HTTPException(status_code=404, detail="Associated quotation not found")

    if action_in.status == PaymentStatus.VERIFIED:
        payment.status = PaymentStatus.VERIFIED
        payment.verified_by_id = current_admin.id
        payment.verified_at = datetime.now(timezone.utc)
        payment.remarks = action_in.remarks
        # Update quotation status to PAYMENT_VERIFIED
        quotation.status = QuotationStatus.PAYMENT_VERIFIED
        db.commit()

        log_audit_event(db, current_admin, "VERIFY_PAYMENT", "Payment", payment.id, {"quotation_id": quotation.id, "amount": str(payment.amount)}, request)
        return {"message": "Payment successfully verified. Quotation is now ready for order confirmation."}

    elif action_in.status == PaymentStatus.REJECTED:
        if not action_in.rejection_reason:
            raise HTTPException(status_code=400, detail="Rejection reason is mandatory when rejecting payment.")
        
        payment.status = PaymentStatus.REJECTED
        payment.rejection_reason = action_in.rejection_reason
        payment.verified_by_id = current_admin.id
        payment.verified_at = datetime.now(timezone.utc)
        payment.remarks = action_in.remarks
        
        # Unfreeze quotation back to ISSUED so agent can submit corrected report
        quotation.status = QuotationStatus.ISSUED
        db.commit()

        log_audit_event(db, current_admin, "REJECT_PAYMENT", "Payment", payment.id, {"reason": action_in.rejection_reason}, request)
        return {"message": "Payment rejected with documented reason. Quotation unfrozen for resolution."}
    else:
        raise HTTPException(status_code=400, detail="Invalid action status")
