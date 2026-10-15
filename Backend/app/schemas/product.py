from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

class ProductBase(BaseModel):
    sku: str = Field(..., min_length=2, max_length=100)
    name: str = Field(..., min_length=2, max_length=255)
    brand: str = "Livguard"
    category: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    specifications: Optional[str] = None
    image_url: Optional[str] = None
    base_price: Decimal = Field(..., gt=0)
    tax_category: str = "STANDARD_GST"
    is_active: bool = True

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    sku: Optional[str] = None
    name: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    specifications: Optional[str] = None
    image_url: Optional[str] = None
    base_price: Optional[Decimal] = None
    tax_category: Optional[str] = None
    is_active: Optional[bool] = None

class PriceUpdate(BaseModel):
    new_price: Decimal = Field(..., gt=0)
    reason: Optional[str] = None

class PriceHistoryResponse(BaseModel):
    id: str
    old_price: Decimal
    new_price: Decimal
    reason: Optional[str] = None
    effective_from: datetime
    created_at: datetime
    changed_by_name: Optional[str] = None

    class Config:
        from_attributes = True

class ProductResponse(ProductBase):
    id: str
    created_at: datetime
    updated_at: datetime
    price_history: List[PriceHistoryResponse] = []

    class Config:
        from_attributes = True
