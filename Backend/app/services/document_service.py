import os
import asyncio
from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright
from datetime import datetime, timezone
import json

import base64
import mimetypes

from app.core.currency import amount_to_words_inr
from app.core.product_categories import get_category_image_url

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "documents")
os.makedirs(OUTPUT_DIR, exist_ok=True)

jinja_env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)

def get_image_data_uri(path_or_url: str) -> str:
    if not path_or_url:
        return ""
    if path_or_url.startswith("data:"):
        return path_or_url
    
    # Try resolving path against common directories
    root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    clean_path = path_or_url.lstrip("/\\")
    
    candidates = [
        path_or_url,
        os.path.join(root_dir, clean_path),
        os.path.join(root_dir, "Backend", clean_path),
        os.path.join(root_dir, "Frontend", "public", clean_path),
        os.path.join(root_dir, "Backend", "uploads", clean_path),
        os.path.join(root_dir, "Backend", "uploads", "products", os.path.basename(clean_path)),
        os.path.join(root_dir, "Frontend", "public", "assets", os.path.basename(clean_path)),
    ]
    
    for c in candidates:
        if os.path.isfile(c):
            try:
                mime_type, _ = mimetypes.guess_type(c)
                if not mime_type:
                    mime_type = "image/jpeg"
                with open(c, "rb") as f:
                    encoded = base64.b64encode(f.read()).decode("utf-8")
                    return f"data:{mime_type};base64,{encoded}"
            except Exception:
                pass
    return path_or_url

class DocumentService:
    get_image_data_uri = staticmethod(get_image_data_uri)

    @staticmethod
    def render_quotation_html(quotation, revision, company_settings) -> str:
        template = jinja_env.get_template("quotation.html")
        
        created_dt = revision.created_at or datetime.now(timezone.utc)
        issue_date_str = created_dt.strftime("%d-%m-%Y")

        # Prioritize historical snapshot for validity period if present
        snap_company = {}
        if revision.company_snapshot:
            try:
                snap_company = json.loads(revision.company_snapshot)
            except Exception:
                pass

        validity_days = snap_company.get("quotation_validity_days") or (company_settings.quotation_validity_days if company_settings else 15)
        expiry_dt = created_dt.timestamp() + (validity_days * 86400)
        expiry_date_str = datetime.fromtimestamp(expiry_dt, tz=timezone.utc).strftime("%d-%m-%Y")

        items_data = []
        for item in revision.items:
            # Resolve image URI: item.image_url -> product.image_url -> category image fallback
            cat = item.product.category if item.product else None
            raw_img = item.image_url or (item.product.image_url if item.product else None) or get_category_image_url(cat)
            data_uri = get_image_data_uri(raw_img) if raw_img else ""
            
            # Parse description bullets
            desc_text = item.description or ""
            desc_lines = [line.strip().lstrip("•-* ").strip() for line in desc_text.split("\n") if line.strip()]

            items_data.append({
                "product_name": item.product_name,
                "sku": item.sku,
                "description": item.description,
                "desc_lines": desc_lines,
                "image_data_uri": data_uri,
                "unit_price": float(item.unit_price),
                "quantity": item.quantity,
                "total_price": float(item.total_price)
            })

        banner_uri = (
            get_image_data_uri("assets/Banner.png")
            or get_image_data_uri("Banner.png")
            or get_image_data_uri("assets/livguard_banner.jpg") 
            or get_image_data_uri("assets/livguard_banner.jpeg")
        )
        logo_quotation_uri = (
            get_image_data_uri("assets/LogoQuotation.png")
            or get_image_data_uri("LogoQuotation.png")
            or get_image_data_uri("assets/livguard_logo.jpg")
        )
        logo_uri = (
            get_image_data_uri("assets/livguard_logo.jpg") 
            or get_image_data_uri("assets/livguard_logo.png")
            or logo_quotation_uri
        )

        total_quantity = sum(item.quantity for item in revision.items)
        amount_words = amount_to_words_inr(revision.grand_total)

        html_content = template.render(
            quotation_number=quotation.quotation_number or "DRAFT",
            revision_label=revision.revision_label,
            issue_date=issue_date_str,
            expiry_date=expiry_date_str,
            total_quantity=total_quantity,
            customer_name=quotation.customer_name,
            customer_mobile=quotation.customer_mobile,
            customer_email=quotation.customer_email,
            customer_address=quotation.customer_address,
            agent_name=quotation.agent.full_name if quotation.agent else "Sales Agent",
            agent_mobile=quotation.agent.mobile if quotation.agent and quotation.agent.mobile else "N/A",
            tax_policy="GST Standard" if not revision.tax_snapshot else json.loads(revision.tax_snapshot).get("policy", "GST Standard"),
            items=items_data,
            subtotal=float(revision.subtotal),
            discount_amount=float(revision.discount_amount),
            coupon_code=revision.coupon_code,
            tax_rate=float(revision.tax_rate),
            tax_amount=float(revision.tax_amount),
            grand_total=float(revision.grand_total),
            amount_in_words=amount_words,
            company=company_settings,
            banner_data_uri=banner_uri,
            logo_quotation_data_uri=logo_quotation_uri,
            logo_data_uri=logo_uri
        )
        return html_content

    @staticmethod
    def render_order_html(order, company_settings) -> str:
        template = jinja_env.get_template("order_received.html")
        quotation = order.quotation
        revision = order.revision
        payment = order.payment

        items_data = []
        for item in revision.items:
            items_data.append({
                "product_name": item.product_name,
                "sku": item.sku,
                "description": item.description,
                "unit_price": float(item.unit_price),
                "quantity": item.quantity
            })

        order_dt = order.order_date or datetime.now(timezone.utc)
        html_content = template.render(
            order_number=order.order_number,
            order_date=order_dt.strftime("%d-%b-%Y"),
            quotation_number=quotation.quotation_number,
            revision_label=revision.revision_label,
            customer_name=quotation.customer_name,
            customer_mobile=quotation.customer_mobile,
            customer_email=quotation.customer_email,
            customer_address=quotation.customer_address,
            confirmed_by_name=order.confirmed_by.full_name if order.confirmed_by else "Admin",
            expected_delivery_date=order.expected_delivery_date.strftime("%d-%b-%Y") if order.expected_delivery_date else None,
            agent_name=quotation.agent.full_name if quotation.agent else "Sales Agent",
            payment_method=payment.payment_method.value if payment else "Direct",
            transaction_ref=payment.transaction_ref if payment else "N/A",
            confirmed_amount=float(order.confirmed_amount),
            items=items_data,
            company=company_settings
        )
        return html_content

    @staticmethod
    async def generate_pdf_from_html(html_content: str) -> bytes:
        def _render_pdf() -> bytes:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.set_content(html_content, wait_until="networkidle")
                pdf_bytes = page.pdf(
                    format="A4",
                    print_background=True,
                    prefer_css_page_size=True,
                    margin={"top": "0mm", "right": "0mm", "bottom": "0mm", "left": "0mm"}
                )
                browser.close()
                return pdf_bytes

        return await asyncio.to_thread(_render_pdf)

    @staticmethod
    async def generate_png_from_html(html_content: str) -> bytes:
        def _render_png() -> bytes:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(
                    viewport={"width": 794, "height": 1123},
                    device_scale_factor=2
                )
                page.set_content(html_content, wait_until="networkidle")
                png_bytes = page.screenshot(type="png", full_page=True)
                browser.close()
                return png_bytes

        return await asyncio.to_thread(_render_png)
