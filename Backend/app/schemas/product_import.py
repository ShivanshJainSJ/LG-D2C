from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime

class ProductImportRowPreview(BaseModel):
    row_idx: int
    sku: str
    product_name: str
    category: str
    category_key: str
    description: Optional[str] = None
    unit_price: float
    image_url: Optional[str] = None
    is_active: Optional[bool] = None
    is_valid: bool
    is_duplicate_in_file: bool
    is_existing_in_db: bool
    errors: List[str] = []
    diff: Optional[Dict[str, Dict[str, Any]]] = None

class ProductImportPreviewResponse(BaseModel):
    filename: str
    file_type: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    file_duplicate_skus_count: int
    db_existing_skus_count: int
    new_skus_count: int
    can_import: bool
    summary: str
    rows: List[ProductImportRowPreview]

class ProductImportExecuteResponse(BaseModel):
    batch_id: str
    filename: str
    conflict_policy: str
    total_rows: int
    inserted_count: int
    updated_count: int
    skipped_count: int
    rejected_count: int
    status: str
    message: str

class ProductImportBatchSummary(BaseModel):
    id: str
    filename: str
    file_type: str
    conflict_policy: str
    total_rows: int
    inserted_count: int
    updated_count: int
    skipped_count: int
    rejected_count: int
    status: str
    imported_by_email: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ProductImportBatchDetail(ProductImportBatchSummary):
    error_summary: Optional[List[Dict[str, Any]]] = None
    row_outcomes: Optional[List[Dict[str, Any]]] = None
