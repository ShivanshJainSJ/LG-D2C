from sqlalchemy import Column, String, DateTime, Text
from app.core.database import Base
from app.models.base import generate_uuid, utc_now

class Customer(Base):
    __tablename__ = "customers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    mobile = Column(String(30), index=True, nullable=False)
    email = Column(String(255), nullable=True)
    address = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
