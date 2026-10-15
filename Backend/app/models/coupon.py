import enum
from sqlalchemy import Column, String, Boolean, DateTime, Numeric, Integer, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import generate_uuid, utc_now

class CouponDiscountType(str, enum.Enum):
    FIXED = "FIXED"
    PERCENTAGE = "PERCENTAGE"

class Coupon(Base):
    __tablename__ = "coupons"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    code = Column(String(50), unique=True, index=True, nullable=False)
    discount_type = Column(Enum(CouponDiscountType), default=CouponDiscountType.PERCENTAGE, nullable=False)
    discount_value = Column(Numeric(12, 2), nullable=False)
    max_discount = Column(Numeric(12, 2), nullable=True) # Applicable for percentage discount caps
    min_subtotal = Column(Numeric(12, 2), default=0, nullable=False)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    usage_limit = Column(Integer, nullable=True) # Overall usage limit
    used_count = Column(Integer, default=0, nullable=False)
    per_agent_limit = Column(Integer, default=10, nullable=True)
    eligible_categories = Column(Text, nullable=True) # JSON list or null for all
    eligible_agent_ids = Column(Text, nullable=True) # JSON list or null for all
    is_active = Column(Boolean, default=True, nullable=False)
    created_by_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    created_by = relationship("User")
    redemptions = relationship("CouponRedemption", back_populates="coupon", cascade="all, delete-orphan")

class CouponRedemption(Base):
    __tablename__ = "coupon_redemptions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    coupon_id = Column(String(36), ForeignKey("coupons.id", ondelete="CASCADE"), nullable=False)
    quotation_id = Column(String(36), nullable=False, index=True)
    agent_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    discount_granted = Column(Numeric(12, 2), nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    coupon = relationship("Coupon", back_populates="redemptions")
    agent = relationship("User")
