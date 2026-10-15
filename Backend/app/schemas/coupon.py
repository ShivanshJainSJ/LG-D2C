from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from app.models.coupon import CouponDiscountType

class CouponBase(BaseModel):
    code: str = Field(..., min_length=2, max_length=50)
    discount_type: CouponDiscountType = CouponDiscountType.PERCENTAGE
    discount_value: Decimal = Field(..., gt=0)
    max_discount: Optional[Decimal] = None
    min_subtotal: Decimal = Field(default=Decimal(0), ge=0)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    usage_limit: Optional[int] = None
    per_agent_limit: Optional[int] = 10
    eligible_categories: Optional[str] = None # JSON string
    eligible_agent_ids: Optional[str] = None # JSON string
    is_active: bool = True

class CouponCreate(CouponBase):
    pass

class CouponUpdate(BaseModel):
    discount_type: Optional[CouponDiscountType] = None
    discount_value: Optional[Decimal] = None
    max_discount: Optional[Decimal] = None
    min_subtotal: Optional[Decimal] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    usage_limit: Optional[int] = None
    per_agent_limit: Optional[int] = None
    eligible_categories: Optional[str] = None
    eligible_agent_ids: Optional[str] = None
    is_active: Optional[bool] = None

class CouponValidateRequest(BaseModel):
    code: str
    subtotal: Decimal
    product_categories: List[str] = []

class CouponValidateResponse(BaseModel):
    valid: bool
    coupon_id: Optional[str] = None
    code: str
    discount_amount: Decimal
    message: str

class CouponResponse(CouponBase):
    id: str
    used_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
