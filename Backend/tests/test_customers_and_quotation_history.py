import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.phone import normalize_phone_number
from app.core.security import create_access_token
from app.models.customer import Customer
from app.models.quotation import Quotation, QuotationRevision, QuotationItem, QuotationStatus
from app.models.product import Product
from app.models.coupon import Coupon, CouponDiscountType
from app.models.user import User, UserRole
from app.models.audit import AuditLog

def test_phone_normalization_formats():
    # Standard 10 digits
    norm, disp = normalize_phone_number("9876543210")
    assert norm == "+919876543210"
    assert disp == "+91 98765 43210"

    # With +91 and spaces
    norm, disp = normalize_phone_number("+91 9876543210")
    assert norm == "+919876543210"

    # With 91- prefix
    norm, disp = normalize_phone_number("91-9876543210")
    assert norm == "+919876543210"

    # With leading 0 (STD/trunk prefix)
    norm, disp = normalize_phone_number("09876543210")
    assert norm == "+919876543210"

    # International number
    norm, disp = normalize_phone_number("+1 555 123 4567")
    assert norm == "+15551234567"

    # Invalid cases
    with pytest.raises(ValueError):
        normalize_phone_number("12345") # Too short
    with pytest.raises(ValueError):
        normalize_phone_number("abcdefghij") # Not digits
    with pytest.raises(ValueError):
        normalize_phone_number("1876543210") # Starts with 1 (not valid Indian mobile)

def test_customer_creation_and_returning_lookup(client: TestClient, db_session: Session):
    agent = db_session.query(User).filter(User.role == UserRole.AGENT).first()
    token = create_access_token(subject=agent.id, role=agent.role.value)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Lookup for non-existing customer
    resp = client.get("/api/v1/customers/lookup?mobile=9811223344", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["found"] is False
    assert data["normalized_mobile"] == "+919811223344"

    # 2. Issue quotation for this customer
    p = db_session.query(Product).first()
    issue_payload = {
        "customer_name": "Rohan Mehra",
        "customer_mobile": "9811223344",
        "customer_email": "rohan@example.com",
        "customer_address": "Sector 14, Gurgaon",
        "items": [
            {"product_id": p.id, "sku": p.sku, "quantity": 1}
        ]
    }
    issue_resp = client.post("/api/v1/agent/quotations/issue", json=issue_payload, headers=headers)
    assert issue_resp.status_code == 200
    q_num = issue_resp.json()["quotation_number"]
    assert q_num.startswith("LG/")

    # 3. Lookup customer days later using formatted number '+91 98112 23344'
    lookup_resp = client.get("/api/v1/customers/lookup?mobile=+91 98112 23344", headers=headers)
    assert lookup_resp.status_code == 200
    lookup_data = lookup_resp.json()
    assert lookup_data["found"] is True
    assert lookup_data["customer"]["name"] == "Rohan Mehra"
    assert lookup_data["customer"]["normalized_mobile"] == "+919811223344"
    assert lookup_data["stats"]["total_quotations"] == 1
    assert lookup_data["stats"]["latest_quotation_number"] == q_num
    assert lookup_data["stats"]["latest_quotation_status"] == "ISSUED"

def test_customer_quotation_history_and_cross_agent_audit(client: TestClient, db_session: Session):
    agent1 = db_session.query(User).filter(User.role == UserRole.AGENT).first()
    
    # Create Agent 2
    agent2 = User(
        email="agent2@livguard.com",
        hashed_password="hash",
        full_name="Pooja Verma",
        role=UserRole.AGENT,
        mobile="9822334455",
        is_active=True
    )
    db_session.add(agent2)
    db_session.flush()

    token2 = create_access_token(subject=agent2.id, role=agent2.role.value)
    headers2 = {"Authorization": f"Bearer {token2}"}

    # Customer created by Agent 1
    customer = Customer(
        name="Amitabh Saxena",
        normalized_mobile="+919833445566",
        mobile_display="+91 98334 45566",
        mobile="9833445566",
        email="amitabh@example.com",
        created_by_agent_id=agent1.id
    )
    db_session.add(customer)
    db_session.flush()

    # Create historical quotation by Agent 1
    p = db_session.query(Product).first()
    quote = Quotation(
        quotation_number="LG/26/HIST-01",
        current_revision_number=0,
        agent_id=agent1.id,
        customer_id=customer.id,
        customer_name=customer.name,
        customer_mobile=customer.normalized_mobile,
        status=QuotationStatus.ISSUED
    )
    db_session.add(quote)
    db_session.flush()

    rev = QuotationRevision(
        quotation_id=quote.id,
        revision_number=0,
        revision_label="Original",
        subtotal=Decimal("30000.00"),
        discount_amount=Decimal("0.00"),
        tax_rate=Decimal("18.00"),
        tax_amount=Decimal("5400.00"),
        grand_total=Decimal("35400.00"),
        is_superseded=False,
        created_by_id=agent1.id
    )
    db_session.add(rev)
    db_session.flush()

    item = QuotationItem(
        revision_id=rev.id,
        product_id=p.id,
        sku=p.sku,
        product_name=p.name,
        unit_price=Decimal("30000.00"),
        quantity=1,
        total_price=Decimal("30000.00")
    )
    db_session.add(item)
    db_session.commit()

    # Agent 2 accesses history of customer created by Agent 1
    history_resp = client.get(f"/api/v1/customers/{customer.id}/quotations", headers=headers2)
    assert history_resp.status_code == 200
    hist = history_resp.json()
    assert hist["total"] == 1
    assert hist["quotations"][0]["quotation_number"] == "LG/26/HIST-01"
    assert hist["quotations"][0]["is_own_quotation"] is False

    # Check audit log was recorded for cross-agent customer view
    audit = db_session.query(AuditLog).filter(
        AuditLog.actor_id == agent2.id,
        AuditLog.action == "VIEW_RETURNING_CUSTOMER_QUOTATIONS"
    ).first()
    assert audit is not None
    assert audit.entity_id == customer.id

def test_quotation_reuse_revalidates_prices_and_protects_original(client: TestClient, db_session: Session):
    agent = db_session.query(User).filter(User.role == UserRole.AGENT).first()
    token = create_access_token(subject=agent.id, role=agent.role.value)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Product setup with original price 10000
    p = db_session.query(Product).filter(Product.sku == "LG-TEST-INV").first()
    p.base_price = Decimal("10000.00")
    db_session.commit()

    # 2. Issue original quotation
    issue_payload = {
        "customer_name": "Suresh Patel",
        "customer_mobile": "9899887766",
        "items": [{"product_id": p.id, "sku": p.sku, "quantity": 2}]
    }
    orig_resp = client.post("/api/v1/agent/quotations/issue", json=issue_payload, headers=headers)
    assert orig_resp.status_code == 200
    orig_id = orig_resp.json()["quotation_id"]
    orig_num = orig_resp.json()["quotation_number"]

    # Original subtotal = 2 * 10000 = 20000, 18% tax = 3600, total = 23600
    orig_quote = db_session.query(Quotation).filter(Quotation.id == orig_id).first()
    assert float(orig_quote.revisions[0].subtotal) == 20000.0
    assert float(orig_quote.revisions[0].grand_total) == 23600.0

    # 3. Product price changes in catalog to 12500
    p.base_price = Decimal("12500.00")
    db_session.commit()

    # 4. Agent reuses quotation
    reuse_resp = client.post(f"/api/v1/agent/quotations/{orig_id}/reuse", headers=headers)
    assert reuse_resp.status_code == 200
    reuse_data = reuse_resp.json()
    new_quote_id = reuse_data["new_quotation_id"]
    assert new_quote_id != orig_id
    assert reuse_data["source_quotation_id"] == orig_id

    # Newly validated pricing: 2 * 12500 = 25000, 18% tax = 4500, total = 29500
    assert reuse_data["subtotal"] == 25000.0
    assert reuse_data["tax_amount"] == 4500.0
    assert reuse_data["grand_total"] == 29500.0

    # 5. Verify original quotation is UNTOUCHED
    db_session.refresh(orig_quote)
    assert orig_quote.quotation_number == orig_num
    assert orig_quote.status == QuotationStatus.ISSUED
    assert float(orig_quote.revisions[0].subtotal) == 20000.0
    assert float(orig_quote.revisions[0].grand_total) == 23600.0

    # 6. Verify new quotation is a DRAFT with source reference
    new_quote = db_session.query(Quotation).filter(Quotation.id == new_quote_id).first()
    assert new_quote.quotation_number is None # Fresh draft
    assert new_quote.status == QuotationStatus.DRAFT
    assert new_quote.source_quotation_id == orig_id
    assert float(new_quote.revisions[0].grand_total) == 29500.0

def test_quotation_reuse_rejects_deactivated_product(client: TestClient, db_session: Session):
    agent = db_session.query(User).filter(User.role == UserRole.AGENT).first()
    token = create_access_token(subject=agent.id, role=agent.role.value)
    headers = {"Authorization": f"Bearer {token}"}

    # Setup quote with active product
    p = db_session.query(Product).first()
    p.is_active = True
    db_session.commit()

    issue_resp = client.post("/api/v1/agent/quotations/issue", json={
        "customer_name": "Deactivate Test",
        "customer_mobile": "9811002233",
        "items": [{"product_id": p.id, "sku": p.sku, "quantity": 1}]
    }, headers=headers)
    q_id = issue_resp.json()["quotation_id"]

    # Deactivate the product
    p.is_active = False
    db_session.commit()

    # Attempting to reuse should be rejected with 400
    resp = client.post(f"/api/v1/agent/quotations/{q_id}/reuse", headers=headers)
    assert resp.status_code == 400
    assert "is deactivated and cannot be reused" in resp.json()["detail"]

def test_invalid_mobile_number_returns_validation_error(client: TestClient, db_session: Session):
    agent = db_session.query(User).filter(User.role == UserRole.AGENT).first()
    token = create_access_token(subject=agent.id, role=agent.role.value)
    headers = {"Authorization": f"Bearer {token}"}
    p = db_session.query(Product).filter(Product.is_active == True).first()

    # Submitting an invalid mobile (e.g. 10 digits starting with 1, 2, 3, 4, 5)
    resp = client.post("/api/v1/agent/quotations/issue", json={
        "customer_name": "Invalid Mobile Test",
        "customer_mobile": "1234567890",
        "items": [{"product_id": p.id, "quantity": 1}]
    }, headers=headers)

    # Must NOT crash with 500; must return 422 or 400 validation error
    assert resp.status_code in (400, 422)
    error_text = str(resp.json())
    assert "Indian mobile numbers must begin with 6, 7, 8, or 9" in error_text

