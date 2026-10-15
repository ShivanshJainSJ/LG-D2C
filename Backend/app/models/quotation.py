import enum
from sqlalchemy import Column, String, Boolean, DateTime, Numeric, Integer, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import generate_uuid, utc_now

class QuotationStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    ISSUED = "ISSUED"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    PAYMENT_VERIFIED = "PAYMENT_VERIFIED"
    ORDER_CONFIRMED = "ORDER_CONFIRMED"
    CANCELLED = "CANCELLED"

class Quotation(Base):
    __tablename__ = "quotations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    quotation_number = Column(String(100), unique=True, index=True, nullable=True) # Generated upon issuance
    current_revision_number = Column(Integer, default=0, nullable=False)
    agent_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    customer_name = Column(String(255), nullable=False)
    customer_mobile = Column(String(30), nullable=False, index=True)
    customer_email = Column(String(255), nullable=True)
    customer_address = Column(Text, nullable=True)
    status = Column(Enum(QuotationStatus), default=QuotationStatus.DRAFT, nullable=False, index=True)
    cancellation_reason = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    agent = relationship("User")
    revisions = relationship("QuotationRevision", back_populates="quotation", cascade="all, delete-orphan", order_by="QuotationRevision.revision_number.desc()")
    payments = relationship("Payment", back_populates="quotation", cascade="all, delete-orphan")
    order = relationship("Order", back_populates="quotation", uselist=False)

class QuotationRevision(Base):
    __tablename__ = "quotation_revisions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    quotation_id = Column(String(36), ForeignKey("quotations.id", ondelete="CASCADE"), nullable=False, index=True)
    revision_number = Column(Integer, default=0, nullable=False) # 0 = Original, 1 = Rev 1, etc.
    revision_label = Column(String(50), default="Original", nullable=False)
    subtotal = Column(Numeric(12, 2), nullable=False)
    discount_amount = Column(Numeric(12, 2), default=0, nullable=False)
    coupon_id = Column(String(36), ForeignKey("coupons.id"), nullable=True)
    coupon_code = Column(String(50), nullable=True)
    tax_rate = Column(Numeric(5, 2), nullable=False) # e.g. 18.00
    tax_amount = Column(Numeric(12, 2), nullable=False)
    grand_total = Column(Numeric(12, 2), nullable=False)
    tax_snapshot = Column(Text, nullable=True) # JSON snapshot of tax policy & rates
    company_snapshot = Column(Text, nullable=True) # JSON snapshot of company details & terms
    is_superseded = Column(Boolean, default=False, nullable=False)
    created_by_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    quotation = relationship("Quotation", back_populates="revisions")
    coupon = relationship("Coupon")
    created_by = relationship("User")
    items = relationship("QuotationItem", back_populates="revision", cascade="all, delete-orphan")

class QuotationItem(Base):
    __tablename__ = "quotation_items"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    revision_id = Column(String(36), ForeignKey("quotation_revisions.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(String(36), ForeignKey("products.id"), nullable=False)
    sku = Column(String(100), nullable=False)
    product_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    unit_price = Column(Numeric(12, 2), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    total_price = Column(Numeric(12, 2), nullable=False)

    revision = relationship("QuotationRevision", back_populates="items")
    product = relationship("Product")

class NumberSequence(Base):
    __tablename__ = "number_sequences"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    sequence_type = Column(String(50), nullable=False, index=True) # "QUOTATION" or "ORDER"
    year_key = Column(String(50), nullable=False, index=True) # e.g. "2026", "26-27", or "GLOBAL"
    current_seq = Column(Integer, default=0, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
