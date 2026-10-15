from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, UploadFile, File, Response
from sqlalchemy.orm import Session
from typing import List, Optional
import csv
import io
from decimal import Decimal

from app.core.database import get_db
from app.core.dependencies import require_admin, log_audit_event
from app.models.user import User
from app.models.product import Product, PriceHistory
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse, PriceHistoryResponse

router = APIRouter(prefix="/admin/products", tags=["Admin Product Management"])

@router.get("", response_model=List[ProductResponse])
def list_products(
    search: Optional[str] = None,
    category: Optional[str] = None,
    is_active: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    query = db.query(Product)
    if search:
        search_filter = f"%{search}%"
        query = query.filter((Product.name.ilike(search_filter)) | (Product.sku.ilike(search_filter)) | (Product.description.ilike(search_filter)))
    if category:
        query = query.filter(Product.category == category)
    if is_active is not None:
        query = query.filter(Product.is_active == is_active)

    products = query.order_by(Product.name.asc()).offset(skip).limit(limit).all()
    return products

@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    prod_in: ProductCreate,
    request: Request,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    existing = db.query(Product).filter(Product.sku == prod_in.sku.strip().upper()).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Product with SKU '{prod_in.sku}' already exists.")

    new_prod = Product(
        sku=prod_in.sku.strip().upper(),
        name=prod_in.name,
        brand=prod_in.brand,
        category=prod_in.category,
        description=prod_in.description,
        specifications=prod_in.specifications,
        image_url=prod_in.image_url,
        base_price=prod_in.base_price,
        tax_category=prod_in.tax_category,
        is_active=prod_in.is_active
    )
    db.add(new_prod)
    db.commit()
    db.refresh(new_prod)

    # Record initial price history
    price_hist = PriceHistory(
        product_id=new_prod.id,
        old_price=Decimal("0.00"),
        new_price=new_prod.base_price,
        changed_by_id=current_admin.id,
        reason="Initial product creation"
    )
    db.add(price_hist)
    db.commit()

    log_audit_event(db, current_admin, "CREATE_PRODUCT", "Product", new_prod.id, {"sku": new_prod.sku, "price": str(new_prod.base_price)}, request)
    return new_prod

@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: str,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.put("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: str,
    prod_in: ProductUpdate,
    request: Request,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if prod_in.sku and prod_in.sku.strip().upper() != product.sku:
        existing = db.query(Product).filter(Product.sku == prod_in.sku.strip().upper()).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Product SKU '{prod_in.sku}' is already in use.")
        product.sku = prod_in.sku.strip().upper()

    if prod_in.name is not None: product.name = prod_in.name
    if prod_in.brand is not None: product.brand = prod_in.brand
    if prod_in.category is not None: product.category = prod_in.category
    if prod_in.description is not None: product.description = prod_in.description
    if prod_in.specifications is not None: product.specifications = prod_in.specifications
    if prod_in.image_url is not None: product.image_url = prod_in.image_url
    if prod_in.tax_category is not None: product.tax_category = prod_in.tax_category
    if prod_in.is_active is not None: product.is_active = prod_in.is_active

    # Check if price changed
    if prod_in.base_price is not None and prod_in.base_price != product.base_price:
        old_price = product.base_price
        product.base_price = prod_in.base_price
        price_hist = PriceHistory(
            product_id=product.id,
            old_price=old_price,
            new_price=prod_in.base_price,
            changed_by_id=current_admin.id,
            reason="Admin product update"
        )
        db.add(price_hist)

    db.commit()
    db.refresh(product)
    log_audit_event(db, current_admin, "UPDATE_PRODUCT", "Product", product.id, {"sku": product.sku}, request)
    return product

@router.delete("/{product_id}")
def archive_product(
    product_id: str,
    request: Request,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Non-negotiable rule: Archive rather than permanently delete
    product.is_active = False
    db.commit()
    log_audit_event(db, current_admin, "ARCHIVE_PRODUCT", "Product", product.id, {"sku": product.sku}, request)
    return {"message": f"Product '{product.name}' has been archived."}

@router.post("/{product_id}/restore")
def restore_product(
    product_id: str,
    request: Request,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product.is_active = True
    db.commit()
    log_audit_event(db, current_admin, "RESTORE_PRODUCT", "Product", product.id, {"sku": product.sku}, request)
    return {"message": f"Product '{product.name}' has been restored."}

@router.get("/export/csv")
def export_products_csv(
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    products = db.query(Product).order_by(Product.sku.asc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["SKU", "Name", "Brand", "Category", "BasePrice", "TaxCategory", "Description", "IsActive"])
    for p in products:
        writer.writerow([p.sku, p.name, p.brand, p.category, str(p.base_price), p.tax_category, p.description or "", p.is_active])
    
    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=livguard_products.csv"}
    )

@router.post("/import/csv")
async def import_products_csv(
    file: UploadFile = File(...),
    request: Request = None,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    contents = await file.read()
    decoded = contents.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(decoded))
    
    created_count = 0
    updated_count = 0
    errors = []

    for row_idx, row in enumerate(reader, start=2):
        sku = row.get("SKU", "").strip().upper()
        name = row.get("Name", "").strip()
        price_str = row.get("BasePrice", "").strip()
        category = row.get("Category", "Inverter").strip()
        brand = row.get("Brand", "Livguard").strip()
        desc = row.get("Description", "").strip()

        if not sku or not name or not price_str:
            errors.append(f"Row {row_idx}: Missing required SKU, Name, or BasePrice")
            continue

        try:
            price = Decimal(price_str)
        except Exception:
            errors.append(f"Row {row_idx}: Invalid price '{price_str}'")
            continue

        existing = db.query(Product).filter(Product.sku == sku).first()
        if existing:
            existing.name = name
            existing.category = category
            existing.description = desc
            if existing.base_price != price:
                old_p = existing.base_price
                existing.base_price = price
                db.add(PriceHistory(
                    product_id=existing.id,
                    old_price=old_p,
                    new_price=price,
                    changed_by_id=current_admin.id,
                    reason="Bulk CSV Import"
                ))
            updated_count += 1
        else:
            new_p = Product(
                sku=sku,
                name=name,
                brand=brand,
                category=category,
                description=desc,
                base_price=price,
                is_active=True
            )
            db.add(new_p)
            db.flush()
            db.add(PriceHistory(
                product_id=new_p.id,
                old_price=Decimal("0.00"),
                new_price=price,
                changed_by_id=current_admin.id,
                reason="Bulk CSV Import"
            ))
            created_count += 1

    db.commit()
    log_audit_event(db, current_admin, "IMPORT_CSV_PRODUCTS", "Product", None, {"created": created_count, "updated": updated_count}, request)
    return {"created": created_count, "updated": updated_count, "errors": errors}
