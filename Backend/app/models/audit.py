from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from app.core.database import Base
from app.models.base import generate_uuid, utc_now

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    actor_id = Column(String(36), nullable=True) # User ID who initiated action
    actor_email = Column(String(255), nullable=True)
    actor_role = Column(String(50), nullable=True)
    action = Column(String(100), nullable=False) # e.g. "PRODUCT_CREATE", "PRICE_UPDATE", "QUOTATION_ISSUE"
    entity_type = Column(String(100), nullable=False) # "Product", "Quotation", "Payment", "Order"
    entity_id = Column(String(100), nullable=True)
    details = Column(Text, nullable=True) # JSON details of change or audit message
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
