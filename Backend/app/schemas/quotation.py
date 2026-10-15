from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from app.models.quotation import QuotationStatus

class QuotationItemInput(BaseModel):
    product_id: str
    quantity: int = Field(..., gt=0)

class QuotationCreateRequest(BaseModel):
    customer_name: str = Field(..., min_length=2, max_length=255)
    customer_mobile: str = Field(..., min_length=10, max_length=15)
    customer_email: Optional[EmailStr] = None
    customer_address: Optional[str] = None
    items: List[QuotationItemInput] = Field(..., min_length=1)
    coupon_code: Optional[str] = None

class QuotationItemResponse(BaseModel):
    id: str
    product_id: str
    sku: str
    product_name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    unit_price: Decimal
    quantity: int
    total_price: Decimal

    model_config = ConfigDict(from_attributes=True)

class QuotationRevisionResponse(BaseModel):
    id: str
    revision_number: int
    revision_label: str
    subtotal: Decimal
    discount_amount: Decimal
    coupon_code: Optional[str] = None
    tax_rate: Decimal
    tax_amount: Decimal
    grand_total: Decimal
    is_superseded: bool
    created_at: datetime
    items: List[QuotationItemResponse] = []

    model_config = ConfigDict(from_attributes=True)

class QuotationResponse(BaseModel):
    id: str
    quotation_number: Optional[str] = None
    current_revision_number: int
    agent_id: str
    agent_name: Optional[str] = None
    customer_name: str
    customer_mobile: str
    customer_email: Optional[str] = None
    customer_address: Optional[str] = None
    status: QuotationStatus
    cancellation_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    revisions: List[QuotationRevisionResponse] = []
    latest_revision: Optional[QuotationRevisionResponse] = None

    model_config = ConfigDict(from_attributes=True)

class QuotationPreviewResponse(BaseModel):
    customer_name: str
    customer_mobile: str
    items: List[dict]
    subtotal: Decimal
    discount_amount: Decimal
    coupon_code: Optional[str] = None
    tax_rate: Decimal
    tax_amount: Decimal
    grand_total: Decimal

class QuotationCancelRequest(BaseModel):
    reason: str = Field(..., min_length=5, max_length=500)
