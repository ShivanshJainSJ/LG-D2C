def get_agent_headers(client, email="test_agent@livguard.com", password="AgentPass123"):
    res = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password
    })
    return {"Authorization": f"Bearer {res.json()['access_token']}"}

def test_quotation_issuance_and_sequential_numbering(client):
    headers = get_agent_headers(client)

    # Fetch active products
    products = client.get("/api/v1/agent/products", headers=headers).json()
    p1 = products[0]

    # Issue first quotation
    issue_payload = {
        "customer_name": "Ramesh Kumar",
        "customer_mobile": "9876543210",
        "customer_email": "ramesh@example.com",
        "customer_address": "Sector 14, Gurugram",
        "items": [
            {"product_id": p1["id"], "quantity": 2}
        ]
    }

    res1 = client.post("/api/v1/agent/quotations/issue", headers=headers, json=issue_payload)
    assert res1.status_code == 200
    q1_data = res1.json()
    assert "LG/26/0001" in q1_data["quotation_number"]

    # Issue second quotation -> must increment sequentially
    res2 = client.post("/api/v1/agent/quotations/issue", headers=headers, json=issue_payload)
    assert res2.status_code == 200
    q2_data = res2.json()
    assert "LG/26/0002" in q2_data["quotation_number"]

def test_quotation_revision_preserves_immutable_history(client):
    headers = get_agent_headers(client)
    products = client.get("/api/v1/agent/products", headers=headers).json()
    p1 = products[0] # base_price 30000

    issue_res = client.post("/api/v1/agent/quotations/issue", headers=headers, json={
        "customer_name": "Anita Verma",
        "customer_mobile": "9812345678",
        "items": [
            {"product_id": p1["id"], "quantity": 1}
        ]
    })
    q_id = issue_res.json()["quotation_id"]

    # Create Revision 1 by adding quantity = 3
    revise_res = client.post(f"/api/v1/agent/quotations/{q_id}/revise", headers=headers, json={
        "customer_name": "Anita Verma",
        "customer_mobile": "9812345678",
        "items": [
            {"product_id": p1["id"], "quantity": 3}
        ]
    })
    assert revise_res.status_code == 200
    assert revise_res.json()["revision_number"] == 1

    # Fetch details: verify Revision 0 and Revision 1 coexist
    detail = client.get(f"/api/v1/agent/quotations/{q_id}", headers=headers).json()
    assert len(detail["revisions"]) == 2

    # Latest revision (index 0) has revision_number 1 and is not superseded
    rev1 = detail["revisions"][0]
    assert rev1["revision_number"] == 1
    assert rev1["revision_label"] == "Revision 1"
    assert rev1["is_superseded"] is False
    assert rev1["items"][0]["quantity"] == 3

    # Original revision (index 1) is preserved and marked superseded
    rev0 = detail["revisions"][1]
    assert rev0["revision_number"] == 0
    assert rev0["revision_label"] == "Original"
    assert rev0["is_superseded"] is True
    assert rev0["items"][0]["quantity"] == 1
