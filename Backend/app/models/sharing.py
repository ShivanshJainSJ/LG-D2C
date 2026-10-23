import enum
from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import generate_uuid, utc_now

class ShareAccessEventType(str, enum.Enum):
    VIEW = "VIEW"
    DOWNLOAD = "DOWNLOAD"

class QuotationArtifact(Base):
    """
    Immutable sealed PDF artifact for a specific quotation revision.
    Each quotation revision has at most one persistent artifact.
    """
    __tablename__ = "quotation_artifacts"
    __table_args__ = (
        Index("ix_quotation_artifacts_quotation_id", "quotation_id"),
        Index("ix_quotation_artifacts_sha256", "sha256_hash"),
    )

    id = Column(String(36), primary_key=True, default=generate_uuid)
    quotation_id = Column(String(36), ForeignKey("quotations.id", ondelete="CASCADE"), nullable=False)
    revision_id = Column(String(36), ForeignKey("quotation_revisions.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    storage_key = Column(String(512), nullable=False)
    storage_provider = Column(String(50), nullable=False, default="local") # "local" or "r2"
    content_type = Column(String(100), nullable=False, default="application/pdf")
    byte_size = Column(Integer, nullable=False)
    sha256_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    quotation = relationship("Quotation", foreign_keys=[quotation_id])
    revision = relationship("QuotationRevision", back_populates="artifact", foreign_keys=[revision_id])

class QuotationShareLink(Base):
    """
    Manually generated public sharing link for an issued quotation revision.
    Only the SHA-256 hash of the token is stored; the plaintext token is never persisted.
    """
    __tablename__ = "quotation_share_links"
    __table_args__ = (
        Index("ix_quotation_share_links_token_hash", "token_hash", unique=True),
        Index("ix_quotation_share_links_lookup", "token_hash", "is_revoked"),
        Index("ix_quotation_share_links_revision", "revision_id", "is_revoked"),
    )

    id = Column(String(36), primary_key=True, default=generate_uuid)
    quotation_id = Column(String(36), ForeignKey("quotations.id", ondelete="CASCADE"), nullable=False, index=True)
    revision_id = Column(String(36), ForeignKey("quotation_revisions.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(64), nullable=False)
    created_by_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    is_revoked = Column(Boolean, default=False, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    revoked_by_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    last_accessed_at = Column(DateTime, nullable=True)

    quotation = relationship("Quotation", back_populates="share_links", foreign_keys=[quotation_id])
    revision = relationship("QuotationRevision", back_populates="share_links", foreign_keys=[revision_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    revoked_by = relationship("User", foreign_keys=[revoked_by_id])
    access_logs = relationship("SharedQuotationAccessLog", back_populates="share_link", cascade="all, delete-orphan")

class SharedQuotationAccessLog(Base):
    """
    Audit log tracking public customer views and PDF downloads.
    Stores anonymized/hashed IP and user-agent metadata.
    """
    __tablename__ = "shared_quotation_access"
    __table_args__ = (
        Index("ix_shared_access_link_event", "share_link_id", "event_type"),
        Index("ix_shared_access_created_at", "created_at"),
    )

    id = Column(String(36), primary_key=True, default=generate_uuid)
    share_link_id = Column(String(36), ForeignKey("quotation_share_links.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(20), nullable=False) # 'VIEW' or 'DOWNLOAD'
    ip_hash = Column(String(64), nullable=True)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    share_link = relationship("QuotationShareLink", back_populates="access_logs")
