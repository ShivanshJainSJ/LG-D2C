from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.dependencies import require_admin, log_audit_event
from app.models.user import User
from app.models.coupon import Coupon, CouponRedemption
from app.schemas.coupon import CouponCreate, CouponUpdate, CouponResponse

router = APIRouter(prefix="/admin/coupons", tags=["Admin Coupon Management"])

@router.get("", response_model=List[CouponResponse])
def list_coupons(
    is_active: Optional[bool] = None,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    query = db.query(Coupon)
    if is_active is not None:
        query = query.filter(Coupon.is_active == is_active)
    return query.order_by(Coupon.created_at.desc()).all()

@router.post("", response_model=CouponResponse, status_code=status.HTTP_201_CREATED)
def create_coupon(
    coupon_in: CouponCreate,
    request: Request,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    clean_code = coupon_in.code.strip().upper()
    existing = db.query(Coupon).filter(Coupon.code == clean_code).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Coupon code '{clean_code}' already exists.")

    new_coupon = Coupon(
        code=clean_code,
        discount_type=coupon_in.discount_type,
        discount_value=coupon_in.discount_value,
        max_discount=coupon_in.max_discount,
        min_subtotal=coupon_in.min_subtotal,
        start_date=coupon_in.start_date,
        end_date=coupon_in.end_date,
        usage_limit=coupon_in.usage_limit,
        per_agent_limit=coupon_in.per_agent_limit,
        eligible_categories=coupon_in.eligible_categories,
        eligible_agent_ids=coupon_in.eligible_agent_ids,
        is_active=coupon_in.is_active,
        created_by_id=current_admin.id
    )
    db.add(new_coupon)
    db.commit()
    db.refresh(new_coupon)

    log_audit_event(db, current_admin, "CREATE_COUPON", "Coupon", new_coupon.id, {"code": new_coupon.code}, request)
    return new_coupon

@router.put("/{coupon_id}", response_model=CouponResponse)
def update_coupon(
    coupon_id: str,
    coupon_in: CouponUpdate,
    request: Request,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon not found")

    if coupon_in.discount_type is not None: coupon.discount_type = coupon_in.discount_type
    if coupon_in.discount_value is not None: coupon.discount_value = coupon_in.discount_value
    if coupon_in.max_discount is not None: coupon.max_discount = coupon_in.max_discount
    if coupon_in.min_subtotal is not None: coupon.min_subtotal = coupon_in.min_subtotal
    if coupon_in.start_date is not None: coupon.start_date = coupon_in.start_date
    if coupon_in.end_date is not None: coupon.end_date = coupon_in.end_date
    if coupon_in.usage_limit is not None: coupon.usage_limit = coupon_in.usage_limit
    if coupon_in.per_agent_limit is not None: coupon.per_agent_limit = coupon_in.per_agent_limit
    if coupon_in.eligible_categories is not None: coupon.eligible_categories = coupon_in.eligible_categories
    if coupon_in.eligible_agent_ids is not None: coupon.eligible_agent_ids = coupon_in.eligible_agent_ids
    if coupon_in.is_active is not None: coupon.is_active = coupon_in.is_active

    db.commit()
    db.refresh(coupon)
    log_audit_event(db, current_admin, "UPDATE_COUPON", "Coupon", coupon.id, {"code": coupon.code}, request)
    return coupon

@router.get("/{coupon_id}/redemptions")
def get_coupon_redemptions(
    coupon_id: str,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    redemptions = db.query(CouponRedemption).filter(CouponRedemption.coupon_id == coupon_id).order_by(CouponRedemption.created_at.desc()).all()
    results = []
    for r in redemptions:
        results.append({
            "id": r.id,
            "quotation_id": r.quotation_id,
            "agent_id": r.agent_id,
            "agent_name": r.agent.full_name if r.agent else "Unknown",
            "discount_granted": float(r.discount_granted),
            "created_at": r.created_at
        })
    return results
