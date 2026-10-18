from sqlalchemy import Column, String, DateTime, Text, Index, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import generate_uuid, utc_now

class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (
        Index("ix_customers_name", "name"),
        Index("ix_customers_created_at", "created_at"),
    )

    id = Column(String(36), primary_key=True, default=generate_uuid)
    normalized_mobile = Column(String(30), unique=True, index=True, nullable=False)
    mobile_display = Column(String(50), nullable=True)
    mobile = Column(String(30), index=True, nullable=True) # Backwards compatibility
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    address = Column(Text, nullable=True)
    created_by_agent_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    last_contacted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    quotations = relationship("Quotation", back_populates="customer", cascade="all, delete-orphan")
    created_by_agent = relationship("User", foreign_keys=[created_by_agent_id])
