import pytest
from decimal import Decimal
from app.services.document_service import DocumentService
from app.models.settings import CompanySettings
from app.models.quotation import Quotation, QuotationRevision, QuotationItem
from app.models.user import User, UserRole
from app.models.product import Product
from app.core.product_categories import (
    ProductCategory,
    CATEGORY_DISPLAY_NAMES,
    CATEGORY_IMAGE_ASSETS,
    normalize_category_key,
    get_category_image_url,
    get_category_display_name,
)

def test_category_definitions_and_asset_resolution():
    categories = [
        "lithium_battery",
        "lead_acid_battery",
        "inverter",
        "lithium_inverter_combo",
        "lead_acid_inverter_combo",
    ]
    for cat in categories:
        norm = normalize_category_key(cat)
        assert norm == cat
        img_url = get_category_image_url(cat)
        assert img_url.startswith("/uploads/products/")
        # Ensure DocumentService resolves the image to a base64 data URI
        data_uri = DocumentService.get_image_data_uri(img_url)
        assert data_uri.startswith("data:image/"), f"Failed for {cat}: {data_uri[:50]}"

    # Test display name normalization
    for key, display in CATEGORY_DISPLAY_NAMES.items():
        assert normalize_category_key(display) == key
        assert get_category_display_name(key) == display

@pytest.mark.anyio
async def test_all_five_categories_document_generation(db_session):
    company = db_session.query(CompanySettings).first()
    agent = db_session.query(User).filter(User.role == UserRole.AGENT).first()

    quote = Quotation(
        quotation_number="LG/2026/CATEGORIES",
        current_revision_number=0,
        agent_id=agent.id,
        customer_name="Livguard Category Showcase Customer",
        customer_mobile="9876543210",
        customer_email="showcase@livguard.com",
        customer_address="Corporate Towers, Phase 1, Gurgaon"
    )
    quote.agent = agent

    rev = QuotationRevision(
        quotation_id=quote.id,
        revision_number=0,
        revision_label="Original",
        subtotal=Decimal("150000.00"),
        discount_amount=Decimal("0.00"),
        coupon_code=None,
        tax_rate=Decimal("18.00"),
        tax_amount=Decimal("27000.00"),
        grand_total=Decimal("177000.00"),
        is_superseded=False,
        created_by_id=agent.id
    )

    items = [
        QuotationItem(
            revision_id=rev.id,
            product_id="prod-1",
            sku="LG-LX-100AH",
            product_name="Lithium Battery Test Item",
            description="Lithium Category Product",
            image_url=get_category_image_url("lithium_battery"),
            unit_price=Decimal("45000.00"),
            quantity=1,
            total_price=Decimal("45000.00")
        ),
        QuotationItem(
            revision_id=rev.id,
            product_id="prod-2",
            sku="LG-BAT-150AH",
            product_name="Lead Acid Battery Test Item",
            description="Lead Acid Category Product",
            image_url=get_category_image_url("lead_acid_battery"),
            unit_price=Decimal("18000.00"),
            quantity=1,
            total_price=Decimal("18000.00")
        ),
        QuotationItem(
            revision_id=rev.id,
            product_id="prod-3",
            sku="LG-INV-1000",
            product_name="Inverter Test Item",
            description="Inverter Category Product",
            image_url=get_category_image_url("inverter"),
            unit_price=Decimal("12000.00"),
            quantity=1,
            total_price=Decimal("12000.00")
        ),
        QuotationItem(
            revision_id=rev.id,
            product_id="prod-4",
            sku="LG-COMBO-PRO100",
            product_name="Lithium Combo Test Item",
            description="Lithium + Inverter Combo",
            image_url=get_category_image_url("lithium_inverter_combo"),
            unit_price=Decimal("55000.00"),
            quantity=1,
            total_price=Decimal("55000.00")
        ),
        QuotationItem(
            revision_id=rev.id,
            product_id="prod-5",
            sku="LG-SET-1",
            product_name="Lead Acid Combo Test Item",
            description="Lead Acid + Inverter Combo",
            image_url=get_category_image_url("lead_acid_inverter_combo"),
            unit_price=Decimal("20000.00"),
            quantity=1,
            total_price=Decimal("20000.00")
        ),
    ]
    rev.items = items
    quote.revisions = [rev]

    html_content = DocumentService.render_quotation_html(quote, rev, company)
    assert "LG/2026/CATEGORIES" in html_content
    assert "LG-LX-100AH" in html_content
    assert "LG-BAT-150AH" in html_content
    assert "LG-INV-1000" in html_content
    assert "LG-COMBO-PRO100" in html_content
    assert "LG-SET-1" in html_content

    # Ensure all 5 items have their images rendered
    for itm in items:
        data_uri = DocumentService.get_image_data_uri(itm.image_url)
        assert data_uri.startswith("data:image/")
        assert data_uri in html_content

    # Generate PDF
    pdf_bytes = await DocumentService.generate_pdf_from_html(html_content)
    assert len(pdf_bytes) > 2000
    assert pdf_bytes.startswith(b"%PDF")

    # Generate PNG
    png_bytes = await DocumentService.generate_png_from_html(html_content)
    assert len(png_bytes) > 2000
    assert png_bytes.startswith(b"\x89PNG")
