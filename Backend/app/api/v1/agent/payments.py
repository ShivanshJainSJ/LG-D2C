import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timezone
from decimal import Decimal

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import require_agent, get_current_user, log_audit_event
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

ALLOWED_EVIDENCE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".pdf"}
MAX_EVIDENCE_SIZE_BYTES = 5 * 1024 * 1024 # 5 MB

@router.post("/upload-evidence")
async def upload_payment_evidence(
    file: UploadFile = File(...),
    current_agent: User = Depends(require_agent)
):
    """
    Securely uploads payment proof/evidence to a protected private directory.
    Validates file extension and size, generating a collision-resistant UUID filename.
    """
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EVIDENCE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{ext}'. Allowed types: {', '.join(ALLOWED_EVIDENCE_EXTENSIONS)}"
        )

    content = await file.read(MAX_EVIDENCE_SIZE_BYTES + 1)
    if len(content) > MAX_EVIDENCE_SIZE_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds maximum allowed size of {MAX_EVIDENCE_SIZE_BYTES // (1024 * 1024)} MB."
        )

    evidence_dir = os.path.join(settings.UPLOAD_DIR, "evidence")
    os.makedirs(evidence_dir, exist_ok=True)

    safe_name = f"{uuid.uuid4().hex}_{os.path.basename(file.filename or 'evidence')}"
    file_path = os.path.join(evidence_dir, safe_name)

    with open(file_path, "wb") as f:
        f.write(content)

    return {
        "evidence_url": f"/api/v1/agent/payments/evidence/{safe_name}",
        "filename": safe_name
    }

@router.get("/evidence/{filename}")
def download_payment_evidence(
    filename: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Securely downloads payment proof/evidence.
    Requires authentication and verifies that the requesting user is either an ADMIN
    or the AGENT who reported the payment.
    """
    clean_filename = os.path.basename(filename)
    evidence_dir = os.path.join(settings.UPLOAD_DIR, "evidence")
    file_path = os.path.join(evidence_dir, clean_filename)

    # Prevent directory traversal attacks
    if not os.path.abspath(file_path).startswith(os.path.abspath(evidence_dir)):
        raise HTTPException(status_code=400, detail="Invalid file path.")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Evidence document not found.")

    # Authorization: Admins have global access, Agents only access their own submissions
    if current_user.role != UserRole.ADMIN:
        payment = db.query(Payment).filter(Payment.evidence_url.contains(clean_filename)).first()
        if payment and payment.reported_by_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Access forbidden: You cannot view payment evidence belonging to another agent."
            )

    return FileResponse(file_path)
