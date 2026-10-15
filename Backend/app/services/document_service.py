import os
from jinja2 import Environment, FileSystemLoader
from playwright.async_api import async_playwright
from datetime import datetime, timezone
import json

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "documents")
os.makedirs(OUTPUT_DIR, exist_ok=True)

jinja_env = Environment(loader=FileSystemLoader(TEMPLATES_DIR), autoescape=True)

class DocumentService:
    @staticmethod
    def render_quotation_html(quotation, revision, company_settings) -> str:
        template = jinja_env.get_template("quotation.html")
        
        created_dt = revision.created_at or datetime.now(timezone.utc)
        issue_date_str = created_dt.strftime("%d-%b-%Y")
        validity_days = company_settings.quotation_validity_days if company_settings else 15
        expiry_dt = created_dt.timestamp() + (validity_days * 86400)
        expiry_date_str = datetime.fromtimestamp(expiry_dt, tz=timezone.utc).strftime("%d-%b-%Y")

        items_data = []
        for item in revision.items:
            items_data.append({
                "product_name": item.product_name,
                "sku": item.sku,
                "description": item.description,
                "unit_price": float(item.unit_price),
                "quantity": item.quantity,
                "total_price": float(item.total_price)
            })

        html_content = template.render(
            quotation_number=quotation.quotation_number or "DRAFT",
            revision_label=revision.revision_label,
            issue_date=issue_date_str,
            expiry_date=expiry_date_str,
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
            company=company_settings
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
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.set_content(html_content, wait_until="networkidle")
            pdf_bytes = await page.pdf(
                format="A4",
                print_background=True,
                prefer_css_page_size=True,
                margin={"top": "0mm", "right": "0mm", "bottom": "0mm", "left": "0mm"}
            )
            await browser.close()
            return pdf_bytes

    @staticmethod
    async def generate_png_from_html(html_content: str) -> bytes:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            # High-DPI viewport (2x resolution for crisp WhatsApp sharing)
            page = await browser.new_page(
                viewport={"width": 794, "height": 1123},
                device_scale_factor=2
            )
            await page.set_content(html_content, wait_until="networkidle")
            png_bytes = await page.screenshot(type="png", full_page=True)
            await browser.close()
            return png_bytes
