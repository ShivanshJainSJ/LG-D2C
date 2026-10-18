import os
import time
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from app.core.config import Settings
from app.models.user import User, UserRole
from app.models.payment import Payment, PaymentStatus, PaymentMethod
from app.models.quotation import Quotation, QuotationRevision, QuotationStatus
from app.core.security import create_access_token, get_password_hash

def test_production_startup_fails_without_secret_key():
    with pytest.raises(ValueError, match="SECRET_KEY must be explicitly set"):
        Settings(ENVIRONMENT="production", SECRET_KEY=None, DATABASE_URL="postgresql://u:p@h/db")

def test_production_startup_fails_with_short_secret_key():
    with pytest.raises(ValueError, match="must be at least 32 characters long"):
        Settings(ENVIRONMENT="production", SECRET_KEY="short-secret-key-too-brief", DATABASE_URL="postgresql://u:p@h/db")

def test_production_startup_fails_with_placeholder_secret_key():
    with pytest.raises(ValueError, match="cannot contain insecure placeholder pattern"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="livguard-production-super-secret-key-change-in-env-982347293847",
            DATABASE_URL="postgresql://u:p@h/db"
        )

def test_production_startup_fails_with_sqlite():
    with pytest.raises(ValueError, match="SQLite cannot be used as a production database"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="a" * 32,
            DATABASE_URL="sqlite:///./livguard.db"
        )

def test_production_startup_succeeds_with_valid_config():
    s = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="a" * 32,
        DATABASE_URL="postgresql://user:pass@remotehost:5432/proddb"
    )
    assert s.ENVIRONMENT == "production"
    assert len(s.SECRET_KEY) == 32

def test_cookie_security_attributes(client: TestClient):
    resp = client.post("/api/v1/auth/login", json={
        "email": "test_admin@livguard.com",
        "password": "AdminPass123"
    })
    assert resp.status_code == 200
    set_cookie_header = resp.headers.get("set-cookie")
    assert set_cookie_header is not None
    assert "access_token" in set_cookie_header
    assert "httponly" in set_cookie_header.lower()
    assert "samesite=lax" in set_cookie_header.lower()
    assert "path=/" in set_cookie_header.lower()
    assert "max-age=" in set_cookie_header.lower()

def test_logout_cookie_cleanup(client: TestClient):
    # Log in first
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "test_admin@livguard.com",
        "password": "AdminPass123"
    })
    token = login_resp.json()["access_token"]

    # Log out
    resp = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    set_cookie_header = resp.headers.get("set-cookie")
    assert set_cookie_header is not None
    assert "access_token=" in set_cookie_header
    assert "max-age=0" in set_cookie_header.lower() or "expires=" in set_cookie_header.lower()

def test_password_complexity_enforcement(client: TestClient, db_session):
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "test_agent@livguard.com",
        "password": "AgentPass123"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Too short (< 8 chars)
    r1 = client.post("/api/v1/auth/change-password", json={"new_password": "short"}, headers=headers)
    assert r1.status_code == 400
    assert "at least 8 characters" in r1.json()["detail"]

    # Only letters
    r2 = client.post("/api/v1/auth/change-password", json={"new_password": "onlylettersalltheway"}, headers=headers)
    assert r2.status_code == 400
    assert "combination of letters and at least one number" in r2.json()["detail"]

    # Only digits
    r3 = client.post("/api/v1/auth/change-password", json={"new_password": "12345678901234"}, headers=headers)
    assert r3.status_code == 400
    assert "combination of letters and at least one number" in r3.json()["detail"]

def test_session_invalidation_after_password_change(client: TestClient, db_session):
    agent = db_session.query(User).filter(User.role == UserRole.AGENT).first()
    # Reset agent password to known value
    agent.hashed_password = get_password_hash("AgentPass123")
    agent.password_changed_at = None
    db_session.commit()

    # 1. Log in and acquire token A
    login_resp = client.post("/api/v1/auth/login", json={
        "email": agent.email,
        "password": "AgentPass123"
    })
    assert login_resp.status_code == 200
    token_a = login_resp.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Verify token A works
    me_resp = client.get("/api/v1/auth/me", headers=headers_a)
    assert me_resp.status_code == 200

    # Ensure a small timestamp advance so password_changed_at is strictly after token_a iat
    time.sleep(1.1)

    # 2. Change password using token A
    change_resp = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "AgentPass123", "new_password": "NewAgentPass456!"},
        headers=headers_a
    )
    assert change_resp.status_code == 200

    # 3. Old token A must now be rejected with 401 Unauthorized
    me_revoked_resp = client.get("/api/v1/auth/me", headers=headers_a)
    assert me_revoked_resp.status_code == 401
    assert "invalidated" in me_revoked_resp.json()["detail"]

    # 4. Logging in with new password succeeds and yields active token B
    login_b = client.post("/api/v1/auth/login", json={
        "email": agent.email,
        "password": "NewAgentPass456!"
    })
    assert login_b.status_code == 200
    token_b = login_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    me_b_resp = client.get("/api/v1/auth/me", headers=headers_b)
    assert me_b_resp.status_code == 200

def test_private_payment_evidence_authorization(client: TestClient, db_session, tmp_path):
    from app.core.config import settings

    agent1 = db_session.query(User).filter(User.role == UserRole.AGENT).first()
    admin = db_session.query(User).filter(User.role == UserRole.ADMIN).first()

    # Create a secondary agent
    agent2 = db_session.query(User).filter(User.email == "second_agent@livguard.com").first()
    if not agent2:
        agent2 = User(
            email="second_agent@livguard.com",
            hashed_password=get_password_hash("AgentPass123"),
            full_name="Second Agent",
            role=UserRole.AGENT,
            is_active=True
        )
        db_session.add(agent2)
        db_session.commit()

    token1 = create_access_token(subject=agent1.id, role=agent1.role.value)
    token2 = create_access_token(subject=agent2.id, role=agent2.role.value)
    admin_token = create_access_token(subject=admin.id, role=admin.role.value)

    # 1. Agent 1 uploads payment evidence
    evidence_content = b"Simulated Bank Transfer Receipt PDF or Image Content"
    upload_resp = client.post(
        "/api/v1/agent/payments/upload-evidence",
        files={"file": ("receipt.png", evidence_content, "image/png")},
        headers={"Authorization": f"Bearer {token1}"}
    )
    assert upload_resp.status_code == 200
    data = upload_resp.json()
    evidence_url = data["evidence_url"]
    filename = data["filename"]

    # Create associated Quotation and Revision record for Agent 1
    quote = Quotation(
        quotation_number="LG/26/TEST-EVID",
        current_revision_number=0,
        agent_id=agent1.id,
        customer_name="Evidence Test Customer",
        customer_mobile="9876543210",
        status=QuotationStatus.ISSUED
    )
    db_session.add(quote)
    db_session.commit()

    rev = QuotationRevision(
        quotation_id=quote.id,
        revision_number=0,
        subtotal=1000,
        discount_amount=0,
        tax_rate=18,
        tax_amount=180,
        grand_total=1180,
        created_by_id=agent1.id
    )
    db_session.add(rev)
    db_session.commit()

    payment = Payment(
        quotation_id=quote.id,
        revision_id=rev.id,
        reported_by_id=agent1.id,
        amount=1180,
        payment_method=PaymentMethod.UPI,
        transaction_ref="UPI-TEST-EVID-999",
        evidence_url=evidence_url,
        status=PaymentStatus.PENDING_REVIEW
    )
    db_session.add(payment)
    db_session.commit()

    # 2. Unauthenticated request to download evidence must return 401
    anon_resp = client.get(f"/api/v1/agent/payments/evidence/{filename}")
    assert anon_resp.status_code == 401

    # 3. Cross-agent attempt (Agent 2 trying to download Agent 1's evidence) must return 403 Forbidden
    cross_resp = client.get(f"/api/v1/agent/payments/evidence/{filename}", headers={"Authorization": f"Bearer {token2}"})
    assert cross_resp.status_code == 403
    assert "forbidden" in cross_resp.json()["detail"].lower()

    # 4. Agent 1 (owner) downloading their own evidence succeeds (200 OK)
    owner_resp = client.get(f"/api/v1/agent/payments/evidence/{filename}", headers={"Authorization": f"Bearer {token1}"})
    assert owner_resp.status_code == 200
    assert owner_resp.content == evidence_content

    # 5. Admin downloading the evidence succeeds (200 OK)
    admin_resp = client.get(f"/api/v1/agent/payments/evidence/{filename}", headers={"Authorization": f"Bearer {admin_token}"})
    assert admin_resp.status_code == 200
    assert admin_resp.content == evidence_content
