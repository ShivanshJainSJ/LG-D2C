from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from collections import defaultdict

from app.core.database import get_db
from app.core.dependencies import require_admin
from app.models.user import User, UserRole
from app.models.quotation import Quotation, QuotationRevision, QuotationItem, QuotationStatus
from app.models.payment import Payment, PaymentStatus
from app.models.order import Order
from app.models.coupon import Coupon

router = APIRouter(prefix="/admin/dashboard", tags=["Admin Dashboard & Analytics"])

@router.get("/metrics")
def get_dashboard_metrics(
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    now = datetime.now(timezone.utc)
    today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)

    all_quotes = db.query(Quotation).all()
    total_quotes = len(all_quotes)
    
    quotes_today = sum(1 for q in all_quotes if q.created_at.replace(tzinfo=timezone.utc) >= today_start)
    quotes_month = sum(1 for q in all_quotes if q.created_at.replace(tzinfo=timezone.utc) >= month_start)

    # Quoted value: sum of latest revision totals
    total_quoted_value = Decimal("0.00")
    for q in all_quotes:
        if q.revisions and q.status != QuotationStatus.CANCELLED:
            total_quoted_value += q.revisions[0].grand_total

    # Payments & Orders metrics
    pending_payments_count = db.query(Payment).filter(Payment.status == PaymentStatus.PENDING_REVIEW).count()
    verified_payments_count = db.query(Payment).filter(Payment.status == PaymentStatus.VERIFIED).count()
    orders_count = db.query(Order).count()

    total_verified_revenue = Decimal("0.00")
    verified_payments = db.query(Payment).filter(Payment.status == PaymentStatus.VERIFIED).all()
    for vp in verified_payments:
        total_verified_revenue += vp.amount

    # Agents count
    active_agents = db.query(User).filter(User.role == UserRole.AGENT, User.is_active == True).count()
    inactive_agents = db.query(User).filter(User.role == UserRole.AGENT, User.is_active == False).count()

    # Coupons used
    coupons = db.query(Coupon).all()
    total_coupons_used = sum(c.used_count for c in coupons)

    return {
        "total_quotations": total_quotes,
        "quotations_today": quotes_today,
        "quotations_this_month": quotes_month,
        "total_quoted_value": float(total_quoted_value),
        "pending_payments_count": pending_payments_count,
        "verified_payments_count": verified_payments_count,
        "orders_received_count": orders_count,
        "total_verified_revenue": float(total_verified_revenue),
        "active_agents": active_agents,
        "inactive_agents": inactive_agents,
        "total_coupons_used": total_coupons_used
    }

@router.get("/charts")
def get_dashboard_charts(
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    now = datetime.now(timezone.utc)
    last_7_days = [(now - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]
    
    quotes_by_day = {day: 0 for day in last_7_days}
    quotations = db.query(Quotation).all()
    for q in quotations:
        day_str = q.created_at.strftime("%Y-%m-%d")
        if day_str in quotes_by_day:
            quotes_by_day[day_str] += 1

    timeline_data = [{"date": k, "count": v} for k, v in quotes_by_day.items()]

    # Agent Performance
    agents = db.query(User).filter(User.role == UserRole.AGENT).all()
    agent_data = []
    for a in agents:
        agent_quotes = db.query(Quotation).filter(Quotation.agent_id == a.id).all()
        q_count = len(agent_quotes)
        q_val = sum(float(q.revisions[0].grand_total) for q in agent_quotes if q.revisions)
        orders = sum(1 for q in agent_quotes if q.status == QuotationStatus.ORDER_CONFIRMED)
        agent_data.append({
            "agent_name": a.full_name,
            "quotation_count": q_count,
            "quoted_value": round(q_val, 2),
            "orders_confirmed": orders,
            "conversion_rate": round(orders / q_count * 100, 1) if q_count > 0 else 0.0
        })

    # Top products by quotation frequency
    items = db.query(QuotationItem).all()
    product_counts = defaultdict(int)
    for itm in items:
        product_counts[itm.product_name] += itm.quantity

    top_products = sorted([{"name": k, "quantity": v} for k, v in product_counts.items()], key=lambda x: x["quantity"], reverse=True)[:5]

    return {
        "timeline": timeline_data,
        "agents": agent_data,
        "top_products": top_products
    }
