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
