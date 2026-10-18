import io
import csv
import json
from decimal import Decimal, InvalidOperation
from typing import List, Dict, Any, Tuple, Optional
from urllib.parse import urlparse
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from sqlalchemy.orm import Session

from app.models.product import Product, PriceHistory
from app.models.product_import import ProductImportBatch
from app.models.user import User
from app.core.product_categories import (
    ProductCategory,
    CATEGORY_DISPLAY_NAMES,
    normalize_category_key,
    get_category_image_url,
    get_category_display_name,
)

CANONICAL_HEADERS = [
    "sku",
    "product_name",
    "category",
    "description",
    "unit_price",
    "image_url",
    "is_active",
]

ALLOWED_CATEGORIES_DISPLAY = [
    "Lithium Battery",
    "Lead Acid Battery",
    "Inverter",
    "Lithium Battery + Inverter combo",
    "Lead Acid Battery + Inverter combo",
]

SAMPLE_ROW = [
    "SAMPLE-LG-INV-1000",
    "Livguard Inverter 1000VA (Sample Data - Do Not Import)",
    "Inverter",
    "Sample pure sine wave inverter for residential use",
    "12500.00",
    "",
    "true",
]

MAX_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_ROWS = 5000

class ProductImportService:

    @staticmethod
    def generate_csv_template() -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(CANONICAL_HEADERS)
        writer.writerow(SAMPLE_ROW)
        return output.getvalue()

    @staticmethod
    def generate_xlsx_template() -> bytes:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Products"

        # Headers
        ws.append(CANONICAL_HEADERS)
        # Sample row
        ws.append(SAMPLE_ROW)

        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        sample_font = Font(name="Calibri", size=10, italic=True, color="64748B")

        for col_idx, col_name in enumerate(CANONICAL_HEADERS, 1):
            cell = ws.cell(row=1, column=col_idx)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="left", vertical="center")

            sample_cell = ws.cell(row=2, column=col_idx)
            sample_cell.font = sample_font

            # Column widths
            ws.column_dimensions[get_column_letter(col_idx)].width = max(len(col_name) + 5, 20)

        ws.column_dimensions["A"].width = 24  # sku
        ws.column_dimensions["B"].width = 40  # product_name
        ws.column_dimensions["C"].width = 32  # category
        ws.column_dimensions["D"].width = 45  # description
        ws.column_dimensions["E"].width = 16  # unit_price
        ws.column_dimensions["F"].width = 30  # image_url
        ws.column_dimensions["G"].width = 14  # is_active

        out_stream = io.BytesIO()
        wb.save(out_stream)
        return out_stream.getvalue()

    @staticmethod
    def is_safe_image_url(url: Optional[str]) -> bool:
        if not url or not url.strip():
            return True
        clean = url.strip()
        if clean.startswith("/uploads/") or clean.startswith("/assets/"):
            return True
        try:
            parsed = urlparse(clean)
            if parsed.scheme in ("http", "https") and parsed.netloc:
                return True
        except Exception:
            return False
        return False

    @staticmethod
    def parse_boolean(val: Any) -> Optional[bool]:
        if val is None:
            return None
        if isinstance(val, bool):
            return val
        s = str(val).strip().lower()
        if not s:
            return None
        if s in ("true", "1", "yes", "y"):
            return True
        if s in ("false", "0", "no", "n"):
            return False
        return None

    @classmethod
    def parse_raw_rows(cls, file_bytes: bytes, filename: str) -> Tuple[List[str], List[Tuple[int, List[Any]]]]:
        """Parses CSV or XLSX into (headers, list of (row_number, row_cells))."""
        ext = filename.lower().split(".")[-1] if "." in filename else ""
        if ext == "csv":
            try:
                decoded = file_bytes.decode("utf-8-sig")
            except UnicodeDecodeError:
                try:
                    decoded = file_bytes.decode("latin-1")
                except Exception as e:
                    raise ValueError(f"Unable to decode CSV file encoding: {str(e)}")

            stream = io.StringIO(decoded)
            reader = csv.reader(stream)
            all_rows = list(reader)
            if not all_rows:
                raise ValueError("Uploaded CSV file is completely empty.")

            raw_header = [str(c).strip().lower() for c in all_rows[0]]
            data_rows = []
            for idx, r in enumerate(all_rows[1:], start=2):
                if not any(str(c).strip() for c in r):
                    continue  # ignore blank line
                data_rows.append((idx, r))
            return raw_header, data_rows

        elif ext in ("xlsx", "xls"):
            try:
                wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=False, read_only=False)
            except Exception as e:
                raise ValueError(f"Unable to parse XLSX file: {str(e)}")

            ws = wb.worksheets[0]
            rows_iter = ws.iter_rows(values_only=False)
            header_row = next(rows_iter, None)
            if not header_row:
                raise ValueError("Uploaded XLSX worksheet is empty.")

            raw_header = []
            for cell in header_row:
                val = str(cell.value).strip().lower() if cell.value is not None else ""
                raw_header.append(val)

            data_rows = []
            for row_idx, row in enumerate(rows_iter, start=2):
                # Check for completely blank row
                values = []
                has_content = False
                for cell in row:
                    val = cell.value
                    if val is not None and str(val).strip():
                        has_content = True
                    # Check for formulas
                    if isinstance(val, str) and val.startswith("="):
                        raise ValueError(f"Formula detected at row {row_idx}, column {cell.column_letter} ('{val}'). Formulas are not permitted in import files.")
                    values.append(val)
                if has_content:
                    data_rows.append((row_idx, values))
            return raw_header, data_rows
        else:
            raise ValueError(f"Unsupported file format '{ext}'. Only .csv and .xlsx files are supported.")

    @classmethod
    def validate_and_preview(cls, file_bytes: bytes, filename: str, db: Session) -> Dict[str, Any]:
        if len(file_bytes) > MAX_FILE_SIZE_BYTES:
            raise ValueError(f"File size exceeds the 5 MB limit ({len(file_bytes)} bytes).")

        raw_header, raw_rows = cls.parse_raw_rows(file_bytes, filename)

        # Validate Canonical Headers and Exact Sequence
        clean_header = [h.strip().lower() for h in raw_header if h.strip()]
        if len(clean_header) < len(CANONICAL_HEADERS):
            raise ValueError(
                f"Missing required column headers. Expected sequence: {', '.join(CANONICAL_HEADERS)}. Found: {', '.join(clean_header)}"
            )

        for i, expected in enumerate(CANONICAL_HEADERS):
            actual = clean_header[i] if i < len(clean_header) else ""
            if actual != expected:
                raise ValueError(
                    f"Column header mismatch at position {i+1}. Expected '{expected}', found '{actual}'. Column sequence must strictly match: {', '.join(CANONICAL_HEADERS)}"
                )

        if len(raw_rows) > MAX_ROWS:
            raise ValueError(f"File contains {len(raw_rows)} rows, exceeding maximum limit of {MAX_ROWS} rows.")

        if not raw_rows:
            raise ValueError("The uploaded file contains headers but no product data rows.")

        # Pass 1: Parse fields and detect in-file duplicates
        sku_occurrences: Dict[str, List[int]] = {}
        parsed_items = []

        for row_idx, r in raw_rows:
            # Map canonical positions
            sku_raw = r[0] if len(r) > 0 else None
            name_raw = r[1] if len(r) > 1 else None
            category_raw = r[2] if len(r) > 2 else None
            desc_raw = r[3] if len(r) > 3 else None
            price_raw = r[4] if len(r) > 4 else None
            image_raw = r[5] if len(r) > 5 else None
            active_raw = r[6] if len(r) > 6 else None

            # Preserve SKU as string (preserving leading zeros)
            sku = str(sku_raw).strip().upper() if sku_raw is not None else ""
            product_name = str(name_raw).strip() if name_raw is not None else ""
            category_str = str(category_raw).strip() if category_raw is not None else ""
            description = str(desc_raw).strip() if desc_raw is not None else ""
            image_url = str(image_raw).strip() if image_raw is not None else ""

            row_errors: List[str] = []

            # Sample row check
            if sku.startswith("SAMPLE-") or "sample data" in product_name.lower():
                row_errors.append("Sample template row detected. Please remove sample rows from actual import data.")

            # Required field checks
            if not sku:
                row_errors.append("SKU is required and cannot be empty.")
            else:
                sku_occurrences.setdefault(sku, []).append(row_idx)

            if not product_name:
                row_errors.append("Product display name is required.")

            if not category_str:
                row_errors.append("Category is required.")
                cat_key = ""
                cat_display = ""
            else:
                cat_key = normalize_category_key(category_str, strict=True)
                if not cat_key:
                    cat_key = ""
                    cat_display = category_str
                    row_errors.append(
                        f"Invalid category '{category_str}'. Must match one of: {', '.join(ALLOWED_CATEGORIES_DISPLAY)}"
                    )
                else:
                    cat_display = get_category_display_name(cat_key)

            # Price validation
            unit_price_val = 0.0
            if price_raw is None or str(price_raw).strip() == "":
                row_errors.append("Unit price is required.")
            else:
                try:
                    p_dec = Decimal(str(price_raw).strip())
                    if p_dec < 0:
                        row_errors.append("Unit price must be a non-negative number.")
                    else:
                        unit_price_val = float(p_dec)
                except (InvalidOperation, ValueError):
                    row_errors.append(f"Invalid unit price '{price_raw}'. Must be a valid numeric amount.")

            # Image URL validation
            if image_url:
                if not cls.is_safe_image_url(image_url):
                    row_errors.append(f"Invalid or unsafe image URL '{image_url}'. Must use http, https, or /uploads/... path.")

            # Active status
            is_active_parsed = cls.parse_boolean(active_raw)
            if active_raw is not None and str(active_raw).strip() != "" and is_active_parsed is None:
                row_errors.append(f"Invalid is_active value '{active_raw}'. Must be true/false, yes/no, or 1/0.")

            parsed_items.append({
                "row_idx": row_idx,
                "sku": sku,
                "product_name": product_name,
                "category": cat_display,
                "category_key": cat_key,
                "description": description,
                "unit_price": unit_price_val,
                "image_url": image_url or None,
                "is_active": is_active_parsed,
                "errors": row_errors,
            })

        # Check for in-file duplicate SKUs
        file_dup_skus = {k: v for k, v in sku_occurrences.items() if len(v) > 1}
        for item in parsed_items:
            sku = item["sku"]
            if sku in file_dup_skus:
                other_rows = [str(r) for r in file_dup_skus[sku]]
                item["is_duplicate_in_file"] = True
                item["errors"].append(
                    f"Duplicate SKU '{sku}' inside uploaded file (found on rows: {', '.join(other_rows)})."
                )
            else:
                item["is_duplicate_in_file"] = False

        # Pass 2: Query database for existing products
        all_skus = [it["sku"] for it in parsed_items if it["sku"]]
        existing_products: Dict[str, Product] = {}
        if all_skus:
            # Query in batches of 500 for DB safety
            for i in range(0, len(all_skus), 500):
                batch = all_skus[i:i+500]
                found = db.query(Product).filter(Product.sku.in_(batch)).all()
                for p in found:
                    existing_products[p.sku] = p

        valid_rows_count = 0
        invalid_rows_count = 0
        db_existing_count = 0
        new_skus_count = 0

        preview_rows = []
        for item in parsed_items:
            sku = item["sku"]
            existing = existing_products.get(sku)
            is_existing = existing is not None
            item["is_existing_in_db"] = is_existing

            if is_existing:
                db_existing_count += 1
                diff = {}
                if existing.name != item["product_name"]:
                    diff["name"] = {"old": existing.name, "new": item["product_name"]}
                if existing.category != item["category_key"] and item["category_key"]:
                    diff["category"] = {
                        "old": get_category_display_name(existing.category),
                        "new": item["category"]
                    }
                if (existing.description or "") != (item["description"] or ""):
                    diff["description"] = {"old": existing.description or "", "new": item["description"] or ""}
                if float(existing.base_price) != float(item["unit_price"]):
                    diff["unit_price"] = {"old": float(existing.base_price), "new": float(item["unit_price"])}
                if item["image_url"] and (existing.image_url or "") != item["image_url"]:
                    diff["image_url"] = {"old": existing.image_url or "Category Default", "new": item["image_url"]}
                if item["is_active"] is not None and existing.is_active != item["is_active"]:
                    diff["is_active"] = {"old": existing.is_active, "new": item["is_active"]}
                item["diff"] = diff
            else:
                new_skus_count += 1
                item["diff"] = None

            is_valid = len(item["errors"]) == 0
            item["is_valid"] = is_valid
            if is_valid:
                valid_rows_count += 1
            else:
                invalid_rows_count += 1

            preview_rows.append(item)

        file_type = filename.lower().split(".")[-1] if "." in filename else "csv"
        can_import = (invalid_rows_count == 0) and (len(file_dup_skus) == 0)

        summary = (
            f"Parsed {len(preview_rows)} rows: {valid_rows_count} valid, {invalid_rows_count} with errors. "
            f"Found {new_skus_count} new SKUs and {db_existing_count} existing SKUs in database."
        )

        return {
            "filename": filename,
            "file_type": file_type,
            "total_rows": len(preview_rows),
            "valid_rows": valid_rows_count,
            "invalid_rows": invalid_rows_count,
            "file_duplicate_skus_count": len(file_dup_skus),
            "db_existing_skus_count": db_existing_count,
            "new_skus_count": new_skus_count,
            "can_import": can_import,
            "summary": summary,
            "rows": preview_rows,
        }

    @classmethod
    def execute_import(
        cls,
        file_bytes: bytes,
        filename: str,
        conflict_policy: str,
        overwrite_confirmed: bool,
        current_admin: User,
        db: Session,
    ) -> ProductImportBatch:
        conflict_policy = conflict_policy.strip().lower()
        if conflict_policy not in ("skip", "overwrite"):
            raise ValueError("Conflict policy must be either 'skip' or 'overwrite'.")

        if conflict_policy == "overwrite" and not overwrite_confirmed:
            raise ValueError(
                "Overwrite confirmation checkbox must be explicitly checked before proceeding with Overwrite policy."
            )

        # Re-validate the entire file on the server
        validation = cls.validate_and_preview(file_bytes, filename, db)
        if not validation["can_import"]:
            err_details = [
                f"Row {r['row_idx']} ({r['sku']}): {'; '.join(r['errors'])}"
                for r in validation["rows"]
                if not r["is_valid"]
            ]
            raise ValueError(
                f"Cannot execute import due to {validation['invalid_rows']} validation errors: " + " | ".join(err_details[:5])
            )

        # Batch transaction execution
        batch_id = None
        inserted_count = 0
        updated_count = 0
        skipped_count = 0
        row_outcomes = []

        try:
            # Create import batch record first
            batch = ProductImportBatch(
                filename=filename,
                file_type=validation["file_type"],
                conflict_policy=conflict_policy,
                total_rows=validation["total_rows"],
                valid_rows=validation["valid_rows"],
                invalid_rows=0,
                status="PROCESSING",
                imported_by_id=current_admin.id,
            )
            db.add(batch)
            db.flush()
            batch_id = batch.id

            for item in validation["rows"]:
                sku = item["sku"]
                existing = db.query(Product).filter(Product.sku == sku).with_for_update().first()

                if existing:
                    if conflict_policy == "skip":
                        skipped_count += 1
                        row_outcomes.append({
                            "row_idx": item["row_idx"],
                            "sku": sku,
                            "action": "SKIPPED",
                            "reason": "Existing product left unchanged per Skip policy."
                        })
                    elif conflict_policy == "overwrite":
                        # Apply updates
                        existing.name = item["product_name"]
                        if item["category_key"]:
                            existing.category = item["category_key"]
                        if item["description"] is not None:
                            existing.description = item["description"]

                        # Image handling:
                        # If image_url provided, use it
                        # If blank, preserve existing custom image if present; if it had category default or empty, assign new category default
                        if item["image_url"]:
                            existing.image_url = item["image_url"]
                        else:
                            if not existing.image_url or "/uploads/products/" in existing.image_url:
                                existing.image_url = get_category_image_url(existing.category)

                        # Active status
                        if item["is_active"] is not None:
                            existing.is_active = item["is_active"]

                        # Price change check
                        new_price = Decimal(str(item["unit_price"]))
                        if existing.base_price != new_price:
                            old_price = existing.base_price
                            existing.base_price = new_price
                            hist = PriceHistory(
                                product_id=existing.id,
                                old_price=old_price,
                                new_price=new_price,
                                changed_by_id=current_admin.id,
                                reason=f"Bulk Import (Batch {batch_id}) - Overwrite"
                            )
                            db.add(hist)

                        updated_count += 1
                        row_outcomes.append({
                            "row_idx": item["row_idx"],
                            "sku": sku,
                            "action": "UPDATED",
                            "reason": "Product details and pricing updated per Overwrite policy."
                        })
                else:
                    # New product insertion
                    assigned_image = item["image_url"] or get_category_image_url(item["category_key"])
                    new_active = item["is_active"] if item["is_active"] is not None else True
                    new_price = Decimal(str(item["unit_price"]))

                    new_prod = Product(
                        sku=sku,
                        name=item["product_name"],
                        brand="Livguard",
                        category=item["category_key"],
                        description=item["description"],
                        base_price=new_price,
                        image_url=assigned_image,
                        is_active=new_active,
                        tax_category="STANDARD_GST"
                    )
                    db.add(new_prod)
                    db.flush()

                    # Record initial price history
                    hist = PriceHistory(
                        product_id=new_prod.id,
                        old_price=Decimal("0.00"),
                        new_price=new_price,
                        changed_by_id=current_admin.id,
                        reason=f"Bulk Import (Batch {batch_id}) - New SKU"
                    )
                    db.add(hist)

                    inserted_count += 1
                    row_outcomes.append({
                        "row_idx": item["row_idx"],
                        "sku": sku,
                        "action": "INSERTED",
                        "reason": "New product successfully cataloged."
                    })

            batch.inserted_count = inserted_count
            batch.updated_count = updated_count
            batch.skipped_count = skipped_count
            batch.rejected_count = 0
            batch.status = "COMPLETED"
            batch.row_outcomes = json.dumps(row_outcomes)
            batch.error_summary = json.dumps([])

            db.commit()
            db.refresh(batch)
            return batch

        except Exception as e:
            db.rollback()
            # If batch record creation succeeded, log failure
            if batch_id:
                try:
                    fail_batch = db.query(ProductImportBatch).filter(ProductImportBatch.id == batch_id).first()
                    if fail_batch:
                        fail_batch.status = "FAILED"
                        fail_batch.error_summary = json.dumps([{"error": str(e)}])
                        db.commit()
                except Exception:
                    pass
            raise e
