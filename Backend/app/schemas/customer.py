from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

class CustomerDetail(BaseModel):
    id: str
    name: str
    normalized_mobile: str
    mobile_display: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    created_at: datetime
    created_by_agent_id: Optional[str] = None
    created_by_agent_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class CustomerQuotationStats(BaseModel):
    total_quotations: int
    latest_quotation_number: Optional[str] = None
    latest_quotation_date: Optional[datetime] = None
    latest_quotation_status: Optional[str] = None
    latest_quotation_grand_total: Optional[float] = None
    created_by_same_agent: bool = True

class CustomerLookupResponse(BaseModel):
    found: bool
    normalized_mobile: str
    mobile_display: str
    customer: Optional[CustomerDetail] = None
    stats: Optional[CustomerQuotationStats] = None

class CustomerHistoryItemProduct(BaseModel):
    product_id: Optional[str] = None
    sku: str
    product_name: str
    quantity: int
    unit_price: float
    total_price: float
    current_catalog_price: Optional[float] = None
    is_active: bool = True

class CustomerQuotationHistoryItem(BaseModel):
    id: str
    quotation_number: str
    revision_number: int
    created_at: datetime
    valid_until: Optional[datetime] = None
    status: str
    subtotal: float
    discount_amount: float
    tax_amount: float
    grand_total: float
    coupon_code: Optional[str] = None
    agent_id: str
    agent_name: str
    is_own_quotation: bool
    items: List[CustomerHistoryItemProduct] = []

class CustomerQuotationHistoryResponse(BaseModel):
    customer_id: str
    customer_name: str
    normalized_mobile: str
    mobile_display: str
    email: Optional[str] = None
    address: Optional[str] = None
    quotations: List[CustomerQuotationHistoryItem]
    total: int
    page: int
    limit: int

class QuotationReuseResponse(BaseModel):
    message: str
    new_quotation_id: str
    source_quotation_id: str
    source_quotation_number: str
    customer_name: str
    customer_mobile: str
    items_count: int
    subtotal: float
    discount_amount: float
    tax_amount: float
    grand_total: float
    coupon_applied: Optional[str] = None
    coupon_warning: Optional[str] = None
    price_updated_notice: str
