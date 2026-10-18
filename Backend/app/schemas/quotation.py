from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from app.models.quotation import QuotationStatus

class QuotationItemInput(BaseModel):
    product_id: str
    quantity: int = Field(..., gt=0)

class QuotationPreviewRequest(BaseModel):
    customer_name: Optional[str] = "Customer Preview"
    customer_mobile: Optional[str] = "9876543210"
    customer_email: Optional[str] = None
    customer_address: Optional[str] = None
    items: List[QuotationItemInput] = Field(..., min_length=1)
    coupon_code: Optional[str] = None

    @field_validator("customer_name", mode="before")
    @classmethod
    def sanitize_preview_name(cls, v):
        if not v or not str(v).strip():
            return "Customer Preview"
        return str(v).strip()

    @field_validator("customer_mobile", mode="before")
    @classmethod
    def sanitize_preview_mobile(cls, v):
        if not v or not str(v).strip():
            return "9876543210"
        return str(v).strip()

    @field_validator("customer_email", mode="before")
    @classmethod
    def sanitize_preview_email(cls, v):
        if not v or not str(v).strip():
            return None
        return str(v).strip()

    @field_validator("customer_address", mode="before")
    @classmethod
    def sanitize_preview_address(cls, v):
        if not v or not str(v).strip():
            return None
        return str(v).strip()

    @field_validator("coupon_code", mode="before")
    @classmethod
    def sanitize_preview_coupon(cls, v):
        if not v or not str(v).strip():
            return None
        return str(v).strip().upper()

class QuotationCreateRequest(BaseModel):
    customer_name: str = Field(..., min_length=1, max_length=255)
    customer_mobile: str = Field(..., min_length=5, max_length=25)
    customer_email: Optional[str] = None
    customer_address: Optional[str] = None
    items: List[QuotationItemInput] = Field(..., min_length=1)
    coupon_code: Optional[str] = None
    source_quotation_id: Optional[str] = None

    @field_validator("customer_name", mode="before")
    @classmethod
    def sanitize_name(cls, v):
        if not v or not str(v).strip():
            raise ValueError("Customer name is required")
        return str(v).strip()

    @field_validator("customer_mobile", mode="before")
    @classmethod
    def sanitize_mobile(cls, v):
        if not v or not str(v).strip():
            raise ValueError("Customer mobile number is required")
        raw = str(v).strip()
        from app.core.phone import normalize_phone_number
        try:
            normalize_phone_number(raw)
        except ValueError as e:
            raise ValueError(f"Invalid mobile number: {str(e)}")
        return raw

    @field_validator("customer_email", mode="before")
    @classmethod
    def sanitize_email(cls, v):
        if not v or not str(v).strip():
            return None
        return str(v).strip()

    @field_validator("customer_address", mode="before")
    @classmethod
    def sanitize_address(cls, v):
        if not v or not str(v).strip():
            return None
        return str(v).strip()

    @field_validator("coupon_code", mode="before")
    @classmethod
    def sanitize_coupon(cls, v):
        if not v or not str(v).strip():
            return None
        return str(v).strip().upper()

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
