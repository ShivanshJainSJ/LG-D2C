from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime
from decimal import Decimal
from app.models.order import OrderStatus

class OrderCreateRequest(BaseModel):
    quotation_id: str
    expected_delivery_date: Optional[datetime] = None
    remarks: Optional[str] = None

class OrderResponse(BaseModel):
    id: str
    order_number: str
    quotation_id: str
    quotation_number: str
    payment_id: str
    confirmed_by_id: str
    confirmed_by_name: Optional[str] = None
    confirmed_amount: Decimal
    order_date: datetime
    expected_delivery_date: Optional[datetime] = None
    remarks: Optional[str] = None
    status: OrderStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
