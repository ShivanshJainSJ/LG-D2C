from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from decimal import Decimal

from app.core.database import get_db
from app.core.dependencies import require_agent
from app.models.user import User
from app.models.quotation import Quotation, QuotationStatus
from app.models.payment import Payment, PaymentStatus
from app.models.order import Order

router = APIRouter(prefix="/agent/dashboard", tags=["Agent Dashboard"])

@router.get("/stats")
def get_agent_stats(
    current_agent: User = Depends(require_agent),
    db: Session = Depends(get_db)
):
    my_quotes = db.query(Quotation).filter(Quotation.agent_id == current_agent.id).all()
    total_quotes = len(my_quotes)
    draft_quotes = sum(1 for q in my_quotes if q.status == QuotationStatus.DRAFT)
    issued_quotes = sum(1 for q in my_quotes if q.status == QuotationStatus.ISSUED)
    payment_pending = sum(1 for q in my_quotes if q.status == QuotationStatus.PAYMENT_PENDING)
    payment_verified = sum(1 for q in my_quotes if q.status == QuotationStatus.PAYMENT_VERIFIED)
    confirmed_orders = sum(1 for q in my_quotes if q.status == QuotationStatus.ORDER_CONFIRMED)

    total_value = Decimal("0.00")
    for q in my_quotes:
        if q.revisions and q.status != QuotationStatus.CANCELLED:
            total_value += q.revisions[0].grand_total

    # Recent activity
    recent_quotes = []
    for q in sorted(my_quotes, key=lambda x: x.created_at, reverse=True)[:5]:
        latest_rev = q.revisions[0] if q.revisions else None
        recent_quotes.append({
            "id": q.id,
            "quotation_number": q.quotation_number or "DRAFT",
            "customer_name": q.customer_name,
            "status": q.status.value,
            "grand_total": float(latest_rev.grand_total) if latest_rev else 0.0,
            "created_at": q.created_at
        })

    return {
        "total_quotations": total_quotes,
        "draft_quotations": draft_quotes,
        "issued_quotations": issued_quotes,
        "payment_pending": payment_pending,
        "payment_verified": payment_verified,
        "confirmed_orders": confirmed_orders,
        "total_quoted_value": float(total_value),
        "conversion_rate": round(confirmed_orders / total_quotes * 100, 1) if total_quotes > 0 else 0.0,
        "recent_quotations": recent_quotes
    }
