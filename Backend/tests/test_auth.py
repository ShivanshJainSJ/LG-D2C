def test_admin_login_success(client):
    response = client.post("/api/v1/auth/login", json={
        "email": "test_admin@livguard.com",
        "password": "AdminPass123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["role"] == "ADMIN"
    assert data["email"] == "test_admin@livguard.com"

def test_agent_login_success(client):
    response = client.post("/api/v1/auth/login", json={
        "email": "test_agent@livguard.com",
        "password": "AgentPass123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["role"] == "AGENT"

def test_login_wrong_password_fails(client):
    response = client.post("/api/v1/auth/login", json={
        "email": "test_admin@livguard.com",
        "password": "WrongPassword!"
    })
    assert response.status_code == 401

def test_agent_cannot_access_admin_endpoints(client):
    # Login as agent
    res = client.post("/api/v1/auth/login", json={
        "email": "test_agent@livguard.com",
        "password": "AgentPass123"
    })
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt to access admin settings
    admin_res = client.get("/api/v1/admin/settings/company", headers=headers)
    assert admin_res.status_code == 403
    assert "Administrative privileges required" in admin_res.json()["detail"]

def test_openapi_security_scheme(client):
    """Verify OpenAPI security scheme exposes HTTPBearer and not OAuth2PasswordBearer."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    security_schemes = data.get("components", {}).get("securitySchemes", {})

    assert "HTTPBearer" in security_schemes
    assert security_schemes["HTTPBearer"]["type"] == "http"
    assert security_schemes["HTTPBearer"]["scheme"] == "bearer"
    assert "OAuth2PasswordBearer" not in security_schemes

def test_login_schema_accepts_json_and_rejects_form(client):
    """Verify login requires JSON and rejects OAuth2 form-urlencoded payload with 422."""
    # JSON login succeeds
    json_resp = client.post("/api/v1/auth/login", json={
        "email": "test_agent@livguard.com",
        "password": "AgentPass123"
    })
    assert json_resp.status_code == 200
    assert json_resp.json()["token_type"] == "bearer"

    # Form-urlencoded payload (Swagger OAuth2 password flow) is rejected with 422
    form_resp = client.post(
        "/api/v1/auth/login",
        data={"username": "test_agent@livguard.com", "password": "AgentPass123", "grant_type": "password"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert form_resp.status_code == 422

def test_bearer_authorization_header(client):
    """Verify standard Bearer token authorization header."""
    res = client.post("/api/v1/auth/login", json={
        "email": "test_agent@livguard.com",
        "password": "AgentPass123"
    })
    token = res.json()["access_token"]

    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "test_agent@livguard.com"

def test_bearer_authorization_tolerates_double_bearer_prefix(client):
    """Verify robustness if user enters 'Bearer <token>' in Swagger UI."""
    res = client.post("/api/v1/auth/login", json={
        "email": "test_agent@livguard.com",
        "password": "AgentPass123"
    })
    token = res.json()["access_token"]

    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer Bearer {token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "test_agent@livguard.com"

def test_raw_authorization_header_without_bearer_is_rejected(client):
    """Verify raw Authorization header without Bearer scheme is rejected with 401."""
    res = client.post("/api/v1/auth/login", json={
        "email": "test_agent@livguard.com",
        "password": "AgentPass123"
    })
    token = res.json()["access_token"]
    client.cookies.clear()

    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": token})
    assert me_resp.status_code == 401
    assert me_resp.headers.get("WWW-Authenticate") == "Bearer"

def test_bearer_authorization_cookie_fallback(client):
    """Verify HTTP-only cookie authentication fallback."""
    res = client.post("/api/v1/auth/login", json={
        "email": "test_agent@livguard.com",
        "password": "AgentPass123"
    })
    token = res.json()["access_token"]

    # Request without Authorization header, using cookie set on client
    client.cookies.clear()
    client.cookies.set("access_token", f"Bearer {token}")
    me_resp = client.get("/api/v1/auth/me")
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "test_agent@livguard.com"

def test_bearer_authorization_missing_and_invalid_token(client):
    """Verify 401 response and WWW-Authenticate header when unauthenticated or token is invalid."""
    # Missing token
    resp_missing = client.get("/api/v1/auth/me")
    assert resp_missing.status_code == 401
    assert resp_missing.headers.get("WWW-Authenticate") == "Bearer"

    # Invalid token
    resp_invalid = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid_token_here"})
    assert resp_invalid.status_code == 401
    assert resp_invalid.headers.get("WWW-Authenticate") == "Bearer"
