import enum
from sqlalchemy import Column, String, DateTime, Numeric, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import generate_uuid, utc_now

class PaymentStatus(str, enum.Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"

class PaymentMethod(str, enum.Enum):
    NEFT_RTGS = "NEFT_RTGS"
    UPI = "UPI"
    NET_BANKING = "NET_BANKING"
    CHEQUE = "CHEQUE"
    CASH = "CASH"

class Payment(Base):
    __tablename__ = "payments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    quotation_id = Column(String(36), ForeignKey("quotations.id", ondelete="CASCADE"), nullable=False, index=True)
    revision_id = Column(String(36), ForeignKey("quotation_revisions.id"), nullable=False)
    reported_by_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    payment_date = Column(DateTime, default=utc_now, nullable=False)
    payment_method = Column(Enum(PaymentMethod), default=PaymentMethod.UPI, nullable=False)
    transaction_ref = Column(String(100), unique=True, index=True, nullable=False)
    evidence_url = Column(String(512), nullable=True)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING_REVIEW, nullable=False, index=True)
    rejection_reason = Column(String(500), nullable=True)
    verified_by_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    quotation = relationship("Quotation", back_populates="payments")
    revision = relationship("QuotationRevision")
    reported_by = relationship("User", foreign_keys=[reported_by_id])
    verified_by = relationship("User", foreign_keys=[verified_by_id])
    order = relationship("Order", back_populates="payment", uselist=False)
