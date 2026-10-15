import enum
from sqlalchemy import Column, String, Boolean, DateTime, Numeric, Integer, Enum, Text
from app.core.database import Base
from app.models.base import generate_uuid, utc_now

class NumberingPolicy(str, enum.Enum):
    CALENDAR_YEAR = "CALENDAR_YEAR" # LG/26/0001
    FINANCIAL_YEAR = "FINANCIAL_YEAR" # LG/26-27/0001
    CONTINUOUS = "CONTINUOUS" # LG/000001

class TaxPricingPolicy(str, enum.Enum):
    EXCLUSIVE = "EXCLUSIVE" # Tax added onto subtotal
    INCLUSIVE = "INCLUSIVE" # Prices include tax

class CompanySettings(Base):
    __tablename__ = "company_settings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    company_name = Column(String(255), default="Livguard Energy Technologies Pvt. Ltd.", nullable=False)
    tagline = Column(String(255), default="More Power. Less Waiting.", nullable=False)
    logo_url = Column(String(512), default="/assets/livguard_logo.png", nullable=True)
    address = Column(Text, default="Plot No. 221, Udyog Vihar, Phase 1, Sector 20, Gurugram, Haryana 122016", nullable=False)
    phone = Column(String(50), default="1800-102-5551", nullable=False)
    email = Column(String(100), default="support@livguard.com", nullable=False)
    website = Column(String(100), default="www.livguard.com", nullable=False)
    terms_conditions = Column(Text, nullable=False)
    quotation_validity_days = Column(Integer, default=15, nullable=False)
    numbering_policy = Column(Enum(NumberingPolicy), default=NumberingPolicy.CALENDAR_YEAR, nullable=False)
    year_boundary_month = Column(Integer, default=4, nullable=False) # April for India FY
    currency_symbol = Column(String(10), default="₹", nullable=False)
    version = Column(Integer, default=1, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

class TaxSettings(Base):
    __tablename__ = "tax_settings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    gst_rate = Column(Numeric(5, 2), default=18.00, nullable=False) # standard 18%
    pricing_policy = Column(Enum(TaxPricingPolicy), default=TaxPricingPolicy.EXCLUSIVE, nullable=False)
    tax_name = Column(String(50), default="GST (18%)", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
