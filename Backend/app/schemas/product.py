from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from app.core.product_categories import (
    normalize_category_key,
    get_category_image_url,
    get_category_display_name,
    CATEGORY_DISPLAY_NAMES
)

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

    @field_validator("category", mode="before")
    @classmethod
    def validate_category(cls, v):
        if not v or not str(v).strip():
            raise ValueError("Category is required")
        norm = normalize_category_key(str(v))
        if not norm:
            allowed = ", ".join(f"'{name}'" for name in CATEGORY_DISPLAY_NAMES.values())
            raise ValueError(f"Invalid category '{v}'. Allowed categories are: {allowed}")
        return norm

    @model_validator(mode="after")
    def set_default_image_if_missing(self):
        if not self.image_url or not str(self.image_url).strip():
            self.image_url = get_category_image_url(self.category)
        return self

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

    @field_validator("category", mode="before")
    @classmethod
    def validate_category(cls, v):
        if v is None:
            return None
        if not str(v).strip():
            return None
        norm = normalize_category_key(str(v))
        if not norm:
            allowed = ", ".join(f"'{name}'" for name in CATEGORY_DISPLAY_NAMES.values())
            raise ValueError(f"Invalid category '{v}'. Allowed categories are: {allowed}")
        return norm

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

    model_config = ConfigDict(from_attributes=True)

class ProductResponse(ProductBase):
    id: str
    category_display: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    price_history: List[PriceHistoryResponse] = []

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="after")
    def populate_category_display_and_image(self):
        if not self.category_display:
            self.category_display = get_category_display_name(self.category)
        if not self.image_url or not str(self.image_url).strip():
            self.image_url = get_category_image_url(self.category)
        return self

