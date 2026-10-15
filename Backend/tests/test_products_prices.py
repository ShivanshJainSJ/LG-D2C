def get_admin_headers(client):
    res = client.post("/api/v1/auth/login", json={
        "email": "test_admin@livguard.com",
        "password": "AdminPass123"
    })
    return {"Authorization": f"Bearer {res.json()['access_token']}"}

def test_sku_uniqueness_enforced(client):
    headers = get_admin_headers(client)
    res = client.post("/api/v1/admin/products", headers=headers, json={
        "sku": "LG-TEST-100", # duplicate of fixture
        "name": "Duplicate SKU Item",
        "brand": "Livguard",
        "category": "Battery",
        "base_price": 25000.0,
        "is_active": True
    })
    assert res.status_code == 400
    assert "already exists" in res.json()["detail"]

def test_product_price_update_records_history(client):
    headers = get_admin_headers(client)
    # Fetch existing product
    prods = client.get("/api/v1/admin/products?search=LG-TEST-100", headers=headers).json()
    prod_id = prods[0]["id"]

    # Update price
    update_res = client.put(f"/api/v1/admin/prices/products/{prod_id}", headers=headers, json={
        "new_price": 32500.00,
        "reason": "Quarterly inflation adjustment"
    })
    assert update_res.status_code == 200

    # Verify price history
    hist_res = client.get(f"/api/v1/admin/prices/products/{prod_id}/history", headers=headers)
    assert hist_res.status_code == 200
    history = hist_res.json()
    assert len(history) >= 1
    assert history[0]["new_price"] == 32500.00
    assert history[0]["reason"] == "Quarterly inflation adjustment"

def test_product_archive_preserves_record(client):
    headers = get_admin_headers(client)
    prods = client.get("/api/v1/admin/products?search=LG-TEST-INV", headers=headers).json()
    prod_id = prods[0]["id"]

    del_res = client.delete(f"/api/v1/admin/products/{prod_id}", headers=headers)
    assert del_res.status_code == 200

    # Ensure it is now archived (is_active = False), not deleted
    archived_prod = client.get(f"/api/v1/admin/products/{prod_id}", headers=headers).json()
    assert archived_prod["is_active"] is False
