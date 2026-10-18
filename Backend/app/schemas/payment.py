from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from decimal import Decimal
from app.models.payment import PaymentStatus, PaymentMethod

class PaymentReportRequest(BaseModel):
    quotation_id: str
    amount: Decimal = Field(..., gt=0)
    payment_method: PaymentMethod
    transaction_ref: str = Field(..., min_length=4, max_length=100)
    payment_date: Optional[datetime] = None
    remarks: Optional[str] = None
    evidence_url: Optional[str] = None

class PaymentVerifyRequest(BaseModel):
    status: PaymentStatus # VERIFIED or REJECTED
    rejection_reason: Optional[str] = None
    remarks: Optional[str] = None

class PaymentResponse(BaseModel):
    id: str
    quotation_id: str
    quotation_number: Optional[str] = None
    revision_id: str
    reported_by_id: str
    reported_by_name: Optional[str] = None
    amount: Decimal
    payment_date: datetime
    payment_method: PaymentMethod
    transaction_ref: str
    evidence_url: Optional[str] = None
    status: PaymentStatus
    rejection_reason: Optional[str] = None
    verified_by_id: Optional[str] = None
    verified_by_name: Optional[str] = None
    verified_at: Optional[datetime] = None
    remarks: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
