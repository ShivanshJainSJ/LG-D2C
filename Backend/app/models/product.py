from sqlalchemy import Column, String, Boolean, DateTime, Numeric, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import generate_uuid, utc_now

class Product(Base):
    __tablename__ = "products"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    sku = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    brand = Column(String(100), default="Livguard", nullable=False)
    category = Column(String(100), index=True, nullable=False) # Inverter, Battery, Solar, Combo
    description = Column(Text, nullable=True)
    specifications = Column(Text, nullable=True) # JSON-serialized specifications
    image_url = Column(String(512), nullable=True)
    base_price = Column(Numeric(12, 2), nullable=False)
    tax_category = Column(String(50), default="STANDARD_GST", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    price_history = relationship("PriceHistory", back_populates="product", cascade="all, delete-orphan")

class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    product_id = Column(String(36), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    old_price = Column(Numeric(12, 2), nullable=False)
    new_price = Column(Numeric(12, 2), nullable=False)
    changed_by_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    effective_from = Column(DateTime, default=utc_now, nullable=False)
    reason = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    product = relationship("Product", back_populates="price_history")
    changed_by = relationship("User")
