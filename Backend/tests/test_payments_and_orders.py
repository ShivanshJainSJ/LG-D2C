def get_auth_headers(client, email, password):
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}

def test_payment_and_order_confirmation_workflow(client):
    agent_headers = get_auth_headers(client, "test_agent@livguard.com", "AgentPass123")
    admin_headers = get_auth_headers(client, "test_admin@livguard.com", "AdminPass123")

    products = client.get("/api/v1/agent/products", headers=agent_headers).json()
    p1 = products[0]

    # 1. Issue quotation
    issue_res = client.post("/api/v1/agent/quotations/issue", headers=agent_headers, json={
        "customer_name": "Suresh Patel",
        "customer_mobile": "9988776655",
        "items": [{"product_id": p1["id"], "quantity": 1}]
    })
    q_id = issue_res.json()["quotation_id"]

    # Fetch total amount
    quote = client.get(f"/api/v1/agent/quotations/{q_id}", headers=agent_headers).json()
    grand_total = quote["revisions"][0]["grand_total"]

    # 2. Try reporting partial / incorrect payment -> must fail
    wrong_payment_res = client.post("/api/v1/agent/payments/report", headers=agent_headers, json={
        "quotation_id": q_id,
        "amount": grand_total - 1000,
        "payment_method": "UPI",
        "transaction_ref": "UPI_TXN_INVALID"
    })
    assert wrong_payment_res.status_code == 400
    assert "must match the full quotation grand total" in wrong_payment_res.json()["detail"]

    # 3. Report full exact payment
    pay_res = client.post("/api/v1/agent/payments/report", headers=agent_headers, json={
        "quotation_id": q_id,
        "amount": grand_total,
        "payment_method": "UPI",
        "transaction_ref": "UPI_TXN_VALID_123"
    })
    assert pay_res.status_code == 201
    payment_id = pay_res.json()["id"]

    # 4. Attempt to revise frozen quotation -> must fail
    revise_attempt = client.post(f"/api/v1/agent/quotations/{q_id}/revise", headers=agent_headers, json={
        "customer_name": "Suresh Patel",
        "customer_mobile": "9988776655",
        "items": [{"product_id": p1["id"], "quantity": 2}]
    })
    assert revise_attempt.status_code == 400
    assert "Cannot revise quotation while payment is under review" in revise_attempt.json()["detail"]

    # 5. Admin verifies payment
    verify_res = client.put(f"/api/v1/admin/payments/{payment_id}/verify", headers=admin_headers, json={
        "status": "VERIFIED",
        "remarks": "Payment received in Livguard HDFC account"
    })
    assert verify_res.status_code == 200

    # 6. Admin confirms order
    order_res = client.post("/api/v1/admin/orders", headers=admin_headers, json={
        "quotation_id": q_id,
        "remarks": "Dispatch priority"
    })
    assert order_res.status_code == 201
    order_data = order_res.json()
    assert "ORD/26/0001" in order_data["order_number"]
    assert order_data["status"] == "CONFIRMED"

    # 7. Check quotation is locked
    updated_quote = client.get(f"/api/v1/agent/quotations/{q_id}", headers=agent_headers).json()
    assert updated_quote["status"] == "ORDER_CONFIRMED"
