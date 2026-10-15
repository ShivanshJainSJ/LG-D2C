from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.dependencies import require_agent
from app.models.user import User
from app.models.product import Product

router = APIRouter(prefix="/agent/products", tags=["Agent Products"])

@router.get("")
def list_active_products(
    search: Optional[str] = None,
    category: Optional[str] = None,
    current_agent: User = Depends(require_agent),
    db: Session = Depends(get_db)
):
    query = db.query(Product).filter(Product.is_active == True)
    if search:
        search_filter = f"%{search}%"
        query = query.filter((Product.name.ilike(search_filter)) | (Product.sku.ilike(search_filter)) | (Product.description.ilike(search_filter)))
    if category:
        query = query.filter(Product.category == category)

    products = query.order_by(Product.name.asc()).all()
    results = []
    for p in products:
        results.append({
            "id": p.id,
            "sku": p.sku,
            "name": p.name,
            "brand": p.brand,
            "category": p.category,
            "description": p.description,
            "image_url": p.image_url,
            "unit_price": float(p.base_price) # Agents can view authorized unit prices
        })
    return results
