import pytest
import hashlib
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.product import Product
from app.models.quotation import Quotation, QuotationRevision, QuotationItem, QuotationStatus
from app.models.sharing import QuotationShareLink, SharedQuotationAccessLog
from app.core.security import create_access_token

def setup_issued_quotation(db_session: Session) -> tuple[Quotation, QuotationRevision, User, User]:
    agent = db_session.query(User).filter(User.role == UserRole.AGENT).first()
    other_agent = User(
        email="other_agent@livguard.com",
        full_name="Other Agent",
        hashed_password="hashed_pass_placeholder",
        role=UserRole.AGENT,
        mobile="7777777777",
        is_active=True
    )
    db_session.add(other_agent)
    db_session.flush()

    product = db_session.query(Product).first()

    quote = Quotation(
        quotation_number="LQ-2026-SHARE-001",
        current_revision_number=0,
        agent_id=agent.id,
        customer_name="Sunita Rao",
        customer_mobile="+919876543210",
        customer_email="sunita@example.com",
        customer_address="Bangalore, Karnataka",
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
        coupon_code=None,
        tax_rate=Decimal("18.00"),
        tax_amount=product.base_price * Decimal("0.18"),
        grand_total=product.base_price * Decimal("1.18"),
        company_snapshot='{"company_name": "Livguard Energy", "phone": "1800-102-5551", "terms": "15 days", "quotation_validity_days": 15}',
        tax_snapshot='{"rate": 18.0, "policy": "GST Standard"}',
        is_superseded=False,
        created_by_id=agent.id
    )
    db_session.add(rev0)
    db_session.flush()

    item0 = QuotationItem(
        revision_id=rev0.id,
        product_id=product.id,
        sku=product.sku,
        product_name=product.name,
        description=product.description,
        unit_price=product.base_price,
        quantity=1,
        total_price=product.base_price
    )
    db_session.add(item0)
    db_session.commit()
    db_session.refresh(quote)
    db_session.refresh(rev0)

    return quote, rev0, agent, other_agent

def test_authorized_agent_creates_share_link(client: TestClient, db_session: Session):
    quote, rev0, agent, _ = setup_issued_quotation(db_session)
    token = create_access_token(subject=agent.id, role=agent.role.value)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. First Share creation
    resp = client.post(f"/api/v1/agent/quotations/{quote.id}/revisions/{rev0.id}/share", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_new"] is True
    assert "raw_token" in data
    assert data["share_url"].startswith("/shared/")
    raw_token = data["raw_token"]

    # Verify token hash is stored in database, NOT raw token
    stored_link = db_session.query(QuotationShareLink).filter(QuotationShareLink.id == data["share_link_id"]).first()
    assert stored_link is not None
    assert stored_link.token_hash == hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    assert stored_link.token_hash != raw_token
    assert stored_link.is_revoked is False

def test_unauthorized_agent_forbidden(client: TestClient, db_session: Session):
    quote, rev0, _, other_agent = setup_issued_quotation(db_session)
    other_token = create_access_token(subject=other_agent.id, role=other_agent.role.value)
    headers = {"Authorization": f"Bearer {other_token}"}

    resp = client.post(f"/api/v1/agent/quotations/{quote.id}/revisions/{rev0.id}/share", headers=headers)
    assert resp.status_code == 403
    assert "belongs to another agent" in resp.json()["detail"]

def test_draft_quotation_cannot_be_shared(client: TestClient, db_session: Session):
    quote, rev0, agent, _ = setup_issued_quotation(db_session)
    quote.status = QuotationStatus.DRAFT
    db_session.commit()

    token = create_access_token(subject=agent.id, role=agent.role.value)
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post(f"/api/v1/agent/quotations/{quote.id}/revisions/{rev0.id}/share", headers=headers)
    assert resp.status_code == 400
    assert "draft quotation" in resp.json()["detail"]

def test_repeated_clicks_do_not_create_duplicate_links_unless_regenerated(client: TestClient, db_session: Session):
    quote, rev0, agent, _ = setup_issued_quotation(db_session)
    token = create_access_token(subject=agent.id, role=agent.role.value)
    headers = {"Authorization": f"Bearer {token}"}

    # First click
    r1 = client.post(f"/api/v1/agent/quotations/{quote.id}/revisions/{rev0.id}/share", headers=headers)
    assert r1.status_code == 200
    assert r1.json()["is_new"] is True

    # Second click without regenerate=True -> returns active link info, does not overwrite
    r2 = client.post(f"/api/v1/agent/quotations/{quote.id}/revisions/{rev0.id}/share", headers=headers)
    assert r2.status_code == 200
    assert r2.json()["is_new"] is False
    assert r2.json()["active_link_exists"] is True

    # Third click with regenerate=True -> revokes previous link and issues new token
    r3 = client.post(f"/api/v1/agent/quotations/{quote.id}/revisions/{rev0.id}/share?regenerate=true", headers=headers)
    assert r3.status_code == 200
    assert r3.json()["is_new"] is True
    assert r3.json()["share_link_id"] != r1.json()["share_link_id"]

    # Verify first link is now marked is_revoked=True
    old_link = db_session.query(QuotationShareLink).filter(QuotationShareLink.id == r1.json()["share_link_id"]).first()
    assert old_link.is_revoked is True

def test_public_customer_access_and_access_tracking(client: TestClient, db_session: Session):
    quote, rev0, agent, _ = setup_issued_quotation(db_session)
    token = create_access_token(subject=agent.id, role=agent.role.value)
    headers = {"Authorization": f"Bearer {token}"}

    # Agent creates link
    resp = client.post(f"/api/v1/agent/quotations/{quote.id}/revisions/{rev0.id}/share", headers=headers)
    raw_token = resp.json()["raw_token"]

    # 1. Customer visits landing page (Unauthenticated)
    pub_resp = client.get(f"/api/v1/public/quotations/{raw_token}")
    assert pub_resp.status_code == 200
    assert "no-store" in pub_resp.headers["cache-control"]
    data = pub_resp.json()
    assert data["quotation_number"] == quote.quotation_number
    assert data["customer_name"] == "Sunita Rao"
    assert data["revision_label"] == "Original"
    assert len(data["items"]) == 1
    assert "pdf_download_url" in data
    # Ensure internal DB IDs are NOT exposed in public payload
    assert "id" not in data
    assert "quotation_id" not in data
    assert "agent_id" not in data

    # 2. Customer downloads PDF (Unauthenticated) with proxy header
    pdf_resp = client.get(
        f"/api/v1/public/quotations/{raw_token}/pdf",
        headers={"X-Forwarded-For": "203.0.113.195, 10.0.0.1"}
    )
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    assert "no-store" in pdf_resp.headers["cache-control"]
    assert pdf_resp.content.startswith(b"%PDF")

    # 3. Verify access logs in DB (1 VIEW, 1 DOWNLOAD)
    link = db_session.query(QuotationShareLink).filter(QuotationShareLink.id == resp.json()["share_link_id"]).first()
    assert len(link.access_logs) == 2
    events = [log.event_type for log in link.access_logs]
    assert "VIEW" in events
    assert "DOWNLOAD" in events

    # 4. Agent views share links history and sees counts
    history_resp = client.get(f"/api/v1/agent/quotations/{quote.id}/share-links", headers=headers)
    assert history_resp.status_code == 200
    history = history_resp.json()
    assert len(history) == 1
    assert history[0]["view_count"] == 1
    assert history[0]["download_count"] == 1
    assert history[0]["is_revoked"] is False

def test_invalid_token_returns_404(client: TestClient):
    resp = client.get("/api/v1/public/quotations/completely_invalid_random_token_1234567890")
    assert resp.status_code == 404
    assert "invalid or has been revoked" in resp.json()["detail"]

def test_revocation_immediately_blocks_public_access(client: TestClient, db_session: Session):
    quote, rev0, agent, _ = setup_issued_quotation(db_session)
    token = create_access_token(subject=agent.id, role=agent.role.value)
    headers = {"Authorization": f"Bearer {token}"}

    # Create link
    resp = client.post(f"/api/v1/agent/quotations/{quote.id}/revisions/{rev0.id}/share", headers=headers)
    raw_token = resp.json()["raw_token"]
    link_id = resp.json()["share_link_id"]

    # Verify link works before revocation
    assert client.get(f"/api/v1/public/quotations/{raw_token}").status_code == 200

    # Agent revokes link
    revoke_resp = client.post(f"/api/v1/agent/quotations/{quote.id}/share-links/{link_id}/revoke", headers=headers)
    assert revoke_resp.status_code == 200

    # Public access immediately fails with 404
    assert client.get(f"/api/v1/public/quotations/{raw_token}").status_code == 404
    assert client.get(f"/api/v1/public/quotations/{raw_token}/pdf").status_code == 404

def test_historical_revision_can_be_shared(client: TestClient, db_session: Session):
    quote, rev0, agent, _ = setup_issued_quotation(db_session)
    token = create_access_token(subject=agent.id, role=agent.role.value)
    headers = {"Authorization": f"Bearer {token}"}

    # Create revision 1
    product = db_session.query(Product).first()
    rev1 = QuotationRevision(
        quotation_id=quote.id,
        revision_number=1,
        revision_label="Revision 1",
        subtotal=product.base_price * 2,
        discount_amount=Decimal("0.00"),
        tax_rate=Decimal("18.00"),
        tax_amount=(product.base_price * 2) * Decimal("0.18"),
        grand_total=(product.base_price * 2) * Decimal("1.18"),
        is_superseded=False,
        created_by_id=agent.id
    )
    db_session.add(rev1)
    db_session.flush()

    item1 = QuotationItem(
        revision_id=rev1.id,
        product_id=product.id,
        sku=product.sku,
        product_name=product.name,
        unit_price=product.base_price,
        quantity=2,
        total_price=product.base_price * 2
    )
    db_session.add(item1)
    rev0.is_superseded = True
    db_session.commit()

    # Share historical revision 0
    resp0 = client.post(f"/api/v1/agent/quotations/{quote.id}/revisions/{rev0.id}/share", headers=headers)
    assert resp0.status_code == 200
    token0 = resp0.json()["raw_token"]

    # Share active revision 1
    resp1 = client.post(f"/api/v1/agent/quotations/{quote.id}/revisions/{rev1.id}/share", headers=headers)
    assert resp1.status_code == 200
    token1 = resp1.json()["raw_token"]

    # Check both return appropriate revision details
    pub0 = client.get(f"/api/v1/public/quotations/{token0}").json()
    pub1 = client.get(f"/api/v1/public/quotations/{token1}").json()

    assert pub0["revision_label"] == "Original"
    assert pub1["revision_label"] == "Revision 1"
    assert pub1["grand_total"] > pub0["grand_total"]
    assert pub0["items"][0]["quantity"] == 1
    assert pub1["items"][0]["quantity"] == 2

def test_trusted_proxy_header_handling_and_spoof_prevention(client: TestClient, db_session: Session):
    from app.core.config import settings

    quote, rev0, agent, _ = setup_issued_quotation(db_session)
    token = create_access_token(subject=agent.id, role=agent.role.value)
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.post(f"/api/v1/agent/quotations/{quote.id}/revisions/{rev0.id}/share", headers=headers)
    raw_token = resp.json()["raw_token"]
    link_id = resp.json()["share_link_id"]

    orig_trust = settings.TRUST_PROXY_HEADERS
    orig_proxies = settings.TRUSTED_PROXIES
    try:
        # 1. Untrusted Client / Proxy Header Spoofing Scenario:
        # An untrusted client sends a fake X-Forwarded-For header
        settings.TRUST_PROXY_HEADERS = False
        settings.TRUSTED_PROXIES = []  # testclient is NOT a trusted proxy

        client.get(
            f"/api/v1/public/quotations/{raw_token}",
            headers={"X-Forwarded-For": "198.51.100.99"}
        )

        log1 = db_session.query(SharedQuotationAccessLog).filter(
            SharedQuotationAccessLog.share_link_id == link_id
        ).order_by(SharedQuotationAccessLog.created_at.desc()).first()

        # The spoofed header 198.51.100.99 must NOT be trusted; the hash is calculated from socket client host
        salt = settings.SECRET_KEY[:16]
        spoofed_hash = hashlib.sha256(f"198.51.100.99_{salt}".encode("utf-8")).hexdigest()[:16]
        assert log1.ip_hash != spoofed_hash

        # 2. Legitimate Reverse Proxy Scenario (e.g. Cloudflare / Nginx):
        # When TRUST_PROXY_HEADERS is True or trusted proxy is configured
        settings.TRUST_PROXY_HEADERS = True
        client.get(
            f"/api/v1/public/quotations/{raw_token}",
            headers={"CF-Connecting-IP": "203.0.113.45"}
        )

        log2 = db_session.query(SharedQuotationAccessLog).filter(
            SharedQuotationAccessLog.share_link_id == link_id
        ).order_by(SharedQuotationAccessLog.created_at.desc()).first()

        trusted_cf_hash = hashlib.sha256(f"203.0.113.45_{salt}".encode("utf-8")).hexdigest()[:16]
        assert log2.ip_hash == trusted_cf_hash

    finally:
        settings.TRUST_PROXY_HEADERS = orig_trust
        settings.TRUSTED_PROXIES = orig_proxies

def test_agent_cannot_manage_other_agent_share_links(client: TestClient, db_session: Session):
    quote, rev0, agent, other_agent = setup_issued_quotation(db_session)
    agent_token = create_access_token(subject=agent.id, role=agent.role.value)
    other_token = create_access_token(subject=other_agent.id, role=other_agent.role.value)

    # Agent A creates link
    resp = client.post(
        f"/api/v1/agent/quotations/{quote.id}/revisions/{rev0.id}/share",
        headers={"Authorization": f"Bearer {agent_token}"}
    )
    assert resp.status_code == 200
    link_id = resp.json()["share_link_id"]

    # Agent B attempts to list Agent A's links -> 403 Forbidden
    list_resp = client.get(
        f"/api/v1/agent/quotations/{quote.id}/share-links",
        headers={"Authorization": f"Bearer {other_token}"}
    )
    assert list_resp.status_code == 403

    # Agent B attempts to revoke Agent A's link -> 403 Forbidden
    revoke_resp = client.post(
        f"/api/v1/agent/quotations/{quote.id}/share-links/{link_id}/revoke",
        headers={"Authorization": f"Bearer {other_token}"}
    )
    assert revoke_resp.status_code == 403
