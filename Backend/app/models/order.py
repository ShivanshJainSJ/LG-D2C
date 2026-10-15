import enum
from sqlalchemy import Column, String, DateTime, Numeric, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import generate_uuid, utc_now

class OrderStatus(str, enum.Enum):
    CONFIRMED = "CONFIRMED"
    PROCESSING = "PROCESSING"
    DISPATCHED = "DISPATCHED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"

class Order(Base):
    __tablename__ = "orders"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    order_number = Column(String(100), unique=True, index=True, nullable=False) # e.g. ORD/26/0001
    quotation_id = Column(String(36), ForeignKey("quotations.id"), nullable=False, unique=True)
    revision_id = Column(String(36), ForeignKey("quotation_revisions.id"), nullable=False)
    payment_id = Column(String(36), ForeignKey("payments.id"), nullable=False, unique=True)
    confirmed_by_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    confirmed_amount = Column(Numeric(12, 2), nullable=False)
    order_date = Column(DateTime, default=utc_now, nullable=False)
    expected_delivery_date = Column(DateTime, nullable=True)
    remarks = Column(Text, nullable=True)
    status = Column(Enum(OrderStatus), default=OrderStatus.CONFIRMED, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    quotation = relationship("Quotation", back_populates="order")
    revision = relationship("QuotationRevision")
    payment = relationship("Payment", back_populates="order")
    confirmed_by = relationship("User")
