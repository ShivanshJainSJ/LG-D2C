import pytest
from fastapi.testclient import TestClient
from app.models.quotation import Quotation, QuotationRevision, QuotationItem, QuotationStatus
from app.models.user import User, UserRole
from decimal import Decimal

def test_liveness_and_readiness_probes(client: TestClient):
    # Liveness
    resp = client.get("/healthz")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "alive"

    # Readiness
    resp_ready = client.get("/readyz")
    assert resp_ready.status_code == 200
    data_ready = resp_ready.json()
    assert data_ready["status"] == "ready"
    assert data_ready["checks"]["database"] == "healthy"
    assert data_ready["checks"]["storage"] == "healthy"

def test_security_headers_and_correlation_id(client: TestClient):
    # Test auto-generated X-Request-ID and security headers
    resp = client.get("/health")
    assert resp.status_code == 200
    assert "X-Request-ID" in resp.headers
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "SAMEORIGIN"
    assert resp.headers["X-XSS-Protection"] == "1; mode=block"
    assert resp.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    # Test custom incoming X-Request-ID propagation
    custom_id = "test-corr-id-998877"
    resp_custom = client.get("/health", headers={"X-Request-ID": custom_id})
    assert resp_custom.headers["X-Request-ID"] == custom_id

def test_rate_limiting_on_auth_login(client: TestClient):
    # The login endpoint is limited to 10 requests per minute
    # Send 12 rapid failed login requests
    status_codes = []
    for _ in range(12):
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "nonexistent@livguard.com", "password": "WrongPassword123"}
        )
        status_codes.append(resp.status_code)

    # At least one request should have received 429 Too Many Requests
    assert 429 in status_codes, f"Expected 429 in status codes: {status_codes}"

def _get_agent_token(db_session) -> str:
    from app.core.security import create_access_token
    agent = db_session.query(User).filter(User.role == UserRole.AGENT).first()
    return create_access_token(subject=agent.id, role=agent.role.value)

def test_rbac_security_barriers(client: TestClient, db_session):
    token = _get_agent_token(db_session)
    headers = {"Authorization": f"Bearer {token}"}

    # Agent cannot view admin company settings
    resp = client.get("/api/v1/admin/settings/company", headers=headers)
    assert resp.status_code in [401, 403]

    # Agent cannot update tax settings
    resp = client.put("/api/v1/admin/settings/tax", json={"gst_rate": 12.0}, headers=headers)
    assert resp.status_code in [401, 403]

    # Agent cannot access admin import history
    resp = client.get("/api/v1/admin/products/import/history", headers=headers)
    assert resp.status_code in [401, 403]

    # Agent cannot verify payments
    resp = client.put("/api/v1/admin/payments/dummy-id/verify", json={"status": "VERIFIED"}, headers=headers)
    assert resp.status_code in [401, 403]

def test_quotation_revision_locking_when_payment_reported(client: TestClient, db_session):
    token = _get_agent_token(db_session)
    headers = {"Authorization": f"Bearer {token}"}
    agent = db_session.query(User).filter(User.role == UserRole.AGENT).first()

    # Create quotation in PAYMENT_PENDING state
    quote = Quotation(
        quotation_number="LG/26/TEST-LOCK",
        current_revision_number=0,
        agent_id=agent.id,
        customer_name="Payment Lock Customer",
        customer_mobile="9876543210",
        status=QuotationStatus.PAYMENT_PENDING
    )
    db_session.add(quote)
    db_session.commit()

    # Attempting to revise this quotation should be rejected with 400
    revise_payload = {
        "customer_name": "Payment Lock Customer",
        "customer_mobile": "9876543210",
        "items": [
            {
                "product_id": "test",
                "sku": "LG-INV-1000",
                "quantity": 1
            }
        ]
    }
    resp = client.post(f"/api/v1/agent/quotations/{quote.id}/revise", json=revise_payload, headers=headers)
    assert resp.status_code == 400
    assert "Cannot revise quotation while payment is under review or verified" in resp.json()["detail"]
