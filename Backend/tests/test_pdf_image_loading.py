import pytest
import re
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services.document_service import DocumentService, get_image_data_uri
from app.core.security import create_access_token
from app.models.quotation import Quotation, QuotationRevision, QuotationItem, QuotationStatus
from app.models.user import User, UserRole
from app.models.product import Product

def test_static_asset_resolution():
    """Verify core branding and category assets resolve to valid base64 data URIs."""
    banner = get_image_data_uri("Banner.png")
    assert banner.startswith("data:image/png;base64,")
    assert len(banner) > 1000

    logo_quotation = get_image_data_uri("LogoQuotation.png")
    assert logo_quotation.startswith("data:image/png;base64,")
    assert len(logo_quotation) > 1000

    logo = get_image_data_uri("livguard_logo.jpg")
    assert logo.startswith("data:image/jpeg;base64,")
    assert len(logo) > 1000

    inverter = get_image_data_uri("inverter.png")
    assert inverter.startswith("data:image/png;base64,")
    assert len(inverter) > 1000

    lead_acid = get_image_data_uri("LeadAcidBattery.jpeg")
    assert lead_acid.startswith("data:image/jpeg;base64,")
    assert len(lead_acid) > 1000

def test_missing_asset_returns_empty_string():
    """Non-existent assets must return empty string rather than broken relative paths."""
    missing = get_image_data_uri("nonexistent_random_image_123.png")
    assert missing == ""

@pytest.mark.anyio
async def test_playwright_verifies_valid_images_and_renders_pdf():
    """HTML with valid data URI image renders successfully."""
    valid_img = get_image_data_uri("livguard_logo.jpg")
    html = f"""
    <!DOCTYPE html>
    <html>
    <body>
        <h1>Test Quotation</h1>
        <img src="{valid_img}" alt="Logo" style="width: 100px;">
    </body>
    </html>
    """
    pdf_bytes = await DocumentService.generate_pdf_from_html(html)
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 500

@pytest.mark.anyio
async def test_playwright_detects_broken_image_and_raises_error():
    """HTML with broken image src fails explicitly instead of generating silent broken placeholder."""
    broken_html = """
    <!DOCTYPE html>
    <html>
    <body>
        <h1>Test Quotation</h1>
        <img src="assets/broken_image_path_that_does_not_exist.png" alt="Broken Asset">
    </body>
    </html>
    """
    with pytest.raises(RuntimeError, match="broken or unrenderable image"):
        await DocumentService.generate_pdf_from_html(broken_html)

def test_download_quotation_pdf_returns_attachment_header(client: TestClient, db_session: Session):
    """Public customer download endpoint sets Content-Disposition: attachment with sanitized filename."""
    agent = db_session.query(User).filter(User.role == UserRole.AGENT).first()
    product = db_session.query(Product).first()

    quote = Quotation(
        quotation_number="LG/26/0001",
        current_revision_number=0,
        agent_id=agent.id,
        customer_name="Suresh Verma",
        customer_mobile="+919876543210",
        status=QuotationStatus.ISSUED
    )
    db_session.add(quote)
    db_session.flush()

    rev0 = QuotationRevision(
        quotation_id=quote.id,
        revision_number=0,
        revision_label="Original",
        subtotal=product.base_price,
        discount_amount=Decimal("0.00"),
        tax_rate=Decimal("18.00"),
        tax_amount=product.base_price * Decimal("0.18"),
        grand_total=product.base_price * Decimal("1.18"),
        company_snapshot='{"company_name": "Livguard"}',
        created_by_id=agent.id
    )
    db_session.add(rev0)
    db_session.flush()

    item0 = QuotationItem(
        revision_id=rev0.id,
        product_id=product.id,
        sku=product.sku,
        product_name=product.name,
        unit_price=product.base_price,
        quantity=1,
        total_price=product.base_price
    )
    db_session.add(item0)
    db_session.commit()

    agent_token = create_access_token(subject=agent.id, role=agent.role.value)
    share_res = client.post(
        f"/api/v1/agent/quotations/{quote.id}/revisions/{rev0.id}/share",
        headers={"Authorization": f"Bearer {agent_token}"}
    )
    assert share_res.status_code == 200
    raw_token = share_res.json()["raw_token"]

    # Customer downloads PDF
    pdf_res = client.get(f"/api/v1/public/quotations/{raw_token}/pdf")
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"

    # Verify attachment header and filename sanitization (no slashes)
    cd = pdf_res.headers.get("content-disposition", "")
    assert cd.startswith("attachment;")
    assert 'filename="Livguard_Quotation_LG_26_0001_Rev0.pdf"' in cd

def test_quotation_template_receives_valid_images_and_renders_cleanly(db_session: Session):
    """Quotation HTML context contains non-empty data URIs for all required branding and item artwork."""
    agent = db_session.query(User).filter(User.role == UserRole.AGENT).first()
    product = db_session.query(Product).first()

    quote = Quotation(
        quotation_number="LG/26/0001",
        current_revision_number=0,
        agent_id=agent.id,
        customer_name="Shivansh Jain",
        customer_mobile="+917900921775",
        status=QuotationStatus.ISSUED
    )
    db_session.add(quote)
    db_session.flush()

    rev0 = QuotationRevision(
        quotation_id=quote.id,
        revision_number=0,
        revision_label="Original",
        subtotal=product.base_price,
        discount_amount=Decimal("0.00"),
        tax_rate=Decimal("18.00"),
        tax_amount=product.base_price * Decimal("0.18"),
        grand_total=product.base_price * Decimal("1.18"),
        created_by_id=agent.id
    )
    db_session.add(rev0)
    db_session.flush()

    item0 = QuotationItem(
        revision_id=rev0.id,
        product_id=product.id,
        sku=product.sku,
        product_name=product.name,
        unit_price=product.base_price,
        quantity=1,
        total_price=product.base_price
    )
    db_session.add(item0)
    db_session.commit()

    html = DocumentService.render_quotation_html(quote, rev0, None)
    assert 'class="header-top-banner"' in html
    assert 'src="data:image/png;base64,' in html
    assert 'class="header-logo-quotation"' in html
    assert 'class="item-thumbnail"' in html
    assert 'alt="Livguard"' in html

def test_staging_repair_artifact_regenerates_pdf(client: TestClient, db_session: Session):
    """Admin repair-artifact endpoint regenerates a revision's stored PDF in staging."""
    admin = db_session.query(User).filter(User.role == UserRole.ADMIN).first()
    product = db_session.query(Product).first()

    quote = Quotation(
        quotation_number="LG/26/REPAIR-01",
        current_revision_number=0,
        agent_id=admin.id,
        customer_name="Test Repair",
        customer_mobile="+919999999999",
        status=QuotationStatus.ISSUED
    )
    db_session.add(quote)
    db_session.flush()

    rev0 = QuotationRevision(
        quotation_id=quote.id,
        revision_number=0,
        revision_label="Original",
        subtotal=product.base_price,
        discount_amount=Decimal("0.00"),
        tax_rate=Decimal("18.00"),
        tax_amount=product.base_price * Decimal("0.18"),
        grand_total=product.base_price * Decimal("1.18"),
        created_by_id=admin.id
    )
    db_session.add(rev0)
    db_session.commit()

    admin_token = create_access_token(subject=admin.id, role=admin.role.value)
    headers = {"Authorization": f"Bearer {admin_token}"}

    # Repair artifact on staging
    repair_res = client.post(
        f"/api/v1/admin/quotations/{quote.id}/revisions/{rev0.id}/repair-artifact",
        headers=headers
    )
    assert repair_res.status_code == 200
    data = repair_res.json()
    assert data["status"] == "repaired"
    assert data["byte_size"] > 10000

def test_production_forbids_artifact_repair(client: TestClient, db_session: Session):
    """Artifact repair is strictly blocked in production environments."""
    from app.core.config import settings
    admin = db_session.query(User).filter(User.role == UserRole.ADMIN).first()
    admin_token = create_access_token(subject=admin.id, role=admin.role.value)
    headers = {
        "Authorization": f"Bearer {admin_token}",
        "X-Forwarded-Proto": "https"
    }

    orig_env = settings.ENVIRONMENT
    try:
        settings.ENVIRONMENT = "production"
        res = client.post(
            "/api/v1/admin/quotations/dummy-id/revisions/dummy-rev/repair-artifact",
            headers=headers
        )
        assert res.status_code == 403
        assert "strictly forbidden in production" in res.json()["detail"]
    finally:
        settings.ENVIRONMENT = orig_env
