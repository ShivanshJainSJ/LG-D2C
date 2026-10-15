import pytest
from app.services.document_service import DocumentService
from app.models.settings import CompanySettings
from app.models.quotation import Quotation, QuotationRevision, QuotationItem
from app.models.user import User, UserRole
from decimal import Decimal

@pytest.mark.anyio
async def test_pdf_and_png_generation(db_session):
    company = db_session.query(CompanySettings).first()
    agent = db_session.query(User).filter(User.role == UserRole.AGENT).first()

    quote = Quotation(
        quotation_number="LG/26/9999",
        current_revision_number=0,
        agent_id=agent.id,
        customer_name="Test Customer Ltd",
        customer_mobile="9876543210",
        customer_email="test@customer.com",
        customer_address="Industrial Area, Phase 2, New Delhi"
    )
    quote.agent = agent

    rev = QuotationRevision(
        quotation_id=quote.id,
        revision_number=0,
        revision_label="Original",
        subtotal=Decimal("45000.00"),
        discount_amount=Decimal("4500.00"),
        coupon_code="LIVGUARD10",
        tax_rate=Decimal("18.00"),
        tax_amount=Decimal("7290.00"),
        grand_total=Decimal("47790.00"),
        is_superseded=False,
        created_by_id=agent.id
    )

    item = QuotationItem(
        revision_id=rev.id,
        product_id="prod-1",
        sku="LG-LX-100AH",
        product_name="Livguard Lithium-X 100Ah Battery",
        description="Smart LiFePO4 Inverter Battery",
        unit_price=Decimal("45000.00"),
        quantity=1,
        total_price=Decimal("45000.00")
    )
    rev.items = [item]
    quote.revisions = [rev]

    html_content = DocumentService.render_quotation_html(quote, rev, company)
    assert "LG/26/9999" in html_content
    assert "LG-LX-100AH" in html_content
    assert "47,790" in html_content

    # Render PDF
    pdf_bytes = await DocumentService.generate_pdf_from_html(html_content)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF")

    # Render PNG
    png_bytes = await DocumentService.generate_png_from_html(html_content)
    assert len(png_bytes) > 1000
    assert png_bytes.startswith(b"\x89PNG")
