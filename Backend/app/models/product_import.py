from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import generate_uuid, utc_now

class ProductImportBatch(Base):
    __tablename__ = "product_import_batches"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(10), nullable=False)  # "csv" or "xlsx"
    conflict_policy = Column(String(20), nullable=False)  # "skip" or "overwrite"
    total_rows = Column(Integer, default=0, nullable=False)
    valid_rows = Column(Integer, default=0, nullable=False)
    invalid_rows = Column(Integer, default=0, nullable=False)
    inserted_count = Column(Integer, default=0, nullable=False)
    updated_count = Column(Integer, default=0, nullable=False)
    skipped_count = Column(Integer, default=0, nullable=False)
    rejected_count = Column(Integer, default=0, nullable=False)
    status = Column(String(20), default="COMPLETED", nullable=False)  # "COMPLETED", "FAILED", "ROLLED_BACK"
    error_summary = Column(Text, nullable=True)  # JSON-encoded errors list
    row_outcomes = Column(Text, nullable=True)  # JSON-encoded row action summary
    imported_by_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    imported_by = relationship("User")
