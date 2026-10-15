from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import datetime
from decimal import Decimal
from app.models.settings import NumberingPolicy, TaxPricingPolicy

class CompanySettingsUpdate(BaseModel):
    company_name: Optional[str] = None
    tagline: Optional[str] = None
    logo_url: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    website: Optional[str] = None
    terms_conditions: Optional[str] = None
    quotation_validity_days: Optional[int] = Field(default=None, gt=0)
    numbering_policy: Optional[NumberingPolicy] = None
    year_boundary_month: Optional[int] = Field(default=None, ge=1, le=12)
    currency_symbol: Optional[str] = None

class CompanySettingsResponse(BaseModel):
    id: str
    company_name: str
    tagline: str
    logo_url: Optional[str] = None
    address: str
    phone: str
    email: str
    website: str
    terms_conditions: str
    quotation_validity_days: int
    numbering_policy: NumberingPolicy
    year_boundary_month: int
    currency_symbol: str
    version: int
    updated_at: datetime

    class Config:
        from_attributes = True

class TaxSettingsUpdate(BaseModel):
    gst_rate: Decimal = Field(..., ge=0, le=100)
    pricing_policy: TaxPricingPolicy
    tax_name: str = "GST"
    is_active: bool = True

class TaxSettingsResponse(BaseModel):
    id: str
    gst_rate: Decimal
    pricing_policy: TaxPricingPolicy
    tax_name: str
    is_active: bool
    version: int
    updated_at: datetime

    class Config:
        from_attributes = True
