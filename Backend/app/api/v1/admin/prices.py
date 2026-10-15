from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from decimal import Decimal

from app.core.database import get_db
from app.core.dependencies import require_admin, log_audit_event
from app.models.user import User
from app.models.product import Product, PriceHistory
from app.schemas.product import PriceUpdate, PriceHistoryResponse

router = APIRouter(prefix="/admin/prices", tags=["Admin Price Management"])

@router.put("/products/{product_id}")
def update_product_price(
    product_id: str,
    price_in: PriceUpdate,
    request: Request,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    old_price = product.base_price
    product.base_price = price_in.new_price

    price_entry = PriceHistory(
        product_id=product.id,
        old_price=old_price,
        new_price=price_in.new_price,
        changed_by_id=current_admin.id,
        reason=price_in.reason or "Admin manual price change"
    )
    db.add(price_entry)
    db.commit()

    log_audit_event(
        db, current_admin, "UPDATE_PRICE", "Product", product.id,
        {"sku": product.sku, "old_price": str(old_price), "new_price": str(price_in.new_price), "reason": price_in.reason},
        request
    )
    return {"message": "Price updated successfully", "product_id": product.id, "new_price": price_in.new_price}

@router.get("/products/{product_id}/history")
def get_price_history(
    product_id: str,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    history = db.query(PriceHistory).filter(PriceHistory.product_id == product_id).order_by(PriceHistory.created_at.desc()).all()
    results = []
    for h in history:
        results.append({
            "id": h.id,
            "old_price": float(h.old_price),
            "new_price": float(h.new_price),
            "reason": h.reason,
            "effective_from": h.effective_from,
            "created_at": h.created_at,
            "changed_by": h.changed_by.full_name if h.changed_by else "Admin"
        })
    return results
