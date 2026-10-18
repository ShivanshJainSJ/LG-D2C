from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, UploadFile, File, Form, Response
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
import csv
import io
import json
from decimal import Decimal

from app.core.database import get_db
from app.core.dependencies import require_admin, log_audit_event
from app.models.user import User
from app.models.product import Product, PriceHistory
from app.models.product_import import ProductImportBatch
from app.schemas.product import ProductCreate, ProductUpdate, ProductResponse, PriceHistoryResponse
from app.schemas.product_import import (
    ProductImportPreviewResponse,
    ProductImportExecuteResponse,
    ProductImportBatchSummary,
    ProductImportBatchDetail,
)
from app.services.product_import_service import ProductImportService
from app.core.product_categories import get_category_image_url

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
        query = query.filter(
            (Product.name.ilike(search_filter))
            | (Product.sku.ilike(search_filter))
            | (Product.description.ilike(search_filter))
        )
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

# -------------------------------------------------------------
# BULK PRODUCT IMPORT ENDPOINTS (Placed before /{product_id})
# -------------------------------------------------------------

@router.get("/import/template/csv")
def download_csv_template(
    current_admin: User = Depends(require_admin)
):
    csv_content = ProductImportService.generate_csv_template()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=Livguard_Product_Import_Template.csv"}
    )

@router.get("/import/template/xlsx")
def download_xlsx_template(
    current_admin: User = Depends(require_admin)
):
    xlsx_bytes = ProductImportService.generate_xlsx_template()
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=Livguard_Product_Import_Template.xlsx"}
    )

@router.post("/import/preview", response_model=ProductImportPreviewResponse)
async def preview_product_import(
    file: UploadFile = File(...),
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    file_bytes = await file.read()
    try:
        preview = ProductImportService.validate_and_preview(file_bytes, file.filename, db)
        return preview
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing import file: {str(e)}")

@router.post("/import/execute", response_model=ProductImportExecuteResponse)
async def execute_product_import(
    file: UploadFile = File(...),
    conflict_policy: str = Form("skip"),
    overwrite_confirmed: bool = Form(False),
    request: Request = None,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    file_bytes = await file.read()
    try:
        batch = ProductImportService.execute_import(
            file_bytes=file_bytes,
            filename=file.filename,
            conflict_policy=conflict_policy,
            overwrite_confirmed=overwrite_confirmed,
            current_admin=current_admin,
            db=db
        )

        log_audit_event(
            db,
            current_admin,
            "BULK_IMPORT_PRODUCTS",
            "ProductImportBatch",
            batch.id,
            {
                "filename": batch.filename,
                "conflict_policy": batch.conflict_policy,
                "inserted": batch.inserted_count,
                "updated": batch.updated_count,
                "skipped": batch.skipped_count,
                "total": batch.total_rows,
            },
            request
        )

        return ProductImportExecuteResponse(
            batch_id=batch.id,
            filename=batch.filename,
            conflict_policy=batch.conflict_policy,
            total_rows=batch.total_rows,
            inserted_count=batch.inserted_count,
            updated_count=batch.updated_count,
            skipped_count=batch.skipped_count,
            rejected_count=batch.rejected_count,
            status=batch.status,
            message=f"Successfully processed {batch.total_rows} items: {batch.inserted_count} added, {batch.updated_count} updated, {batch.skipped_count} skipped."
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute product import: {str(e)}")

@router.get("/import/history", response_model=List[ProductImportBatchSummary])
def get_import_history(
    skip: int = 0,
    limit: int = 50,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    batches = db.query(ProductImportBatch).order_by(ProductImportBatch.created_at.desc()).offset(skip).limit(limit).all()
    results = []
    for b in batches:
        results.append(ProductImportBatchSummary(
            id=b.id,
            filename=b.filename,
            file_type=b.file_type,
            conflict_policy=b.conflict_policy,
            total_rows=b.total_rows,
            inserted_count=b.inserted_count,
            updated_count=b.updated_count,
            skipped_count=b.skipped_count,
            rejected_count=b.rejected_count,
            status=b.status,
            imported_by_email=b.imported_by.email if b.imported_by else None,
            created_at=b.created_at
        ))
    return results

@router.get("/import/history/{batch_id}", response_model=ProductImportBatchDetail)
def get_import_batch_detail(
    batch_id: str,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    batch = db.query(ProductImportBatch).filter(ProductImportBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Import batch not found.")

    error_summary = json.loads(batch.error_summary) if batch.error_summary else []
    row_outcomes = json.loads(batch.row_outcomes) if batch.row_outcomes else []

    return ProductImportBatchDetail(
        id=batch.id,
        filename=batch.filename,
        file_type=batch.file_type,
        conflict_policy=batch.conflict_policy,
        total_rows=batch.total_rows,
        inserted_count=batch.inserted_count,
        updated_count=batch.updated_count,
        skipped_count=batch.skipped_count,
        rejected_count=batch.rejected_count,
        status=batch.status,
        imported_by_email=batch.imported_by.email if batch.imported_by else None,
        created_at=batch.created_at,
        error_summary=error_summary,
        row_outcomes=row_outcomes
    )

@router.get("/import/history/{batch_id}/errors.csv")
def download_batch_errors_csv(
    batch_id: str,
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    batch = db.query(ProductImportBatch).filter(ProductImportBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Import batch not found.")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Row Number", "SKU", "Action", "Reason"])

    row_outcomes = json.loads(batch.row_outcomes) if batch.row_outcomes else []
    for item in row_outcomes:
        writer.writerow([
            item.get("row_idx", ""),
            item.get("sku", ""),
            item.get("action", ""),
            item.get("reason", "")
        ])

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=Livguard_Import_Report_{batch.id}.csv"}
    )

# -------------------------------------------------------------
# STANDARD PRODUCT CRUD & EXPORT ENDPOINTS
# -------------------------------------------------------------

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
    if prod_in.category is not None:
        product.category = prod_in.category
        if prod_in.image_url is None and (not product.image_url or "/uploads/products/" in product.image_url):
            product.image_url = get_category_image_url(product.category)
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
