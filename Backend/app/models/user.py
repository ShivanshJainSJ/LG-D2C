import enum
from sqlalchemy import Column, String, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import generate_uuid, utc_now

class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    AGENT = "AGENT"

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.AGENT, nullable=False)
    mobile = Column(String(30), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    last_active_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    login_history = relationship("LoginHistory", back_populates="user", cascade="all, delete-orphan")

class LoginHistory(Base):
    __tablename__ = "login_history"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(512), nullable=True)
    status = Column(String(20), nullable=False) # SUCCESS, FAILED
    created_at = Column(DateTime, default=utc_now, nullable=False)

    user = relationship("User", back_populates="login_history")
