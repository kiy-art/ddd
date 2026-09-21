def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_admin_requires_token(client):
    resp = client.get("/api/admin/products")
    assert resp.status_code == 401


def test_admin_rejects_wrong_token(client):
    resp = client.get("/api/admin/products", headers={"Authorization": "Bearer wrong"})
    assert resp.status_code == 401


def test_create_product_then_public_list_hides_insufficient_data(client, admin_headers):
    resp = client.post(
        "/api/admin/products",
        headers=admin_headers,
        json={
            "name": "G440 Driver",
            "brand": "PING",
            "category": "driver",
            "model_number": "G440",
        },
    )
    assert resp.status_code == 201
    product = resp.json()
    assert product["slug"] == "ping-g440-driver"
    assert product["buy_score"] == "insufficient_data"

    public = client.get("/api/products").json()
    assert public == []  # insufficient_data is not published


def test_adding_prices_updates_buy_score_and_publishes(client, admin_headers):
    created = client.post(
        "/api/admin/products",
        headers=admin_headers,
        json={"name": "G430 Iron", "brand": "PING", "category": "iron"},
    ).json()
    product_id = created["id"]

    for price in [10000, 10000]:
        resp = client.post(
            f"/api/admin/products/{product_id}/prices",
            headers=admin_headers,
            json={"price": price},
        )
        assert resp.status_code == 201

    resp = client.post(
        f"/api/admin/products/{product_id}/prices",
        headers=admin_headers,
        json={"price": 7900},  # 79% of 10000 avg -> strong_buy
    )
    updated = resp.json()
    assert updated["buy_score"] == "strong_buy"
    assert updated["buy_reason"]
    assert updated["ai_title"]  # rule-based fallback since no API key in tests
    assert updated["buy_signal_score"] is not None
    assert 1 <= updated["buy_signal_score"] <= 99
    assert updated["history_span_days"] >= 0

    detail = client.get(f"/api/products/{updated['slug']}").json()
    assert len(detail["price_history"]) == 3

    by_category = client.get("/api/categories/iron").json()
    assert len(by_category) == 1


def test_unknown_category_404(client):
    resp = client.get("/api/categories/not-a-category")
    assert resp.status_code == 404


def test_list_brands_and_brand_filter(client, admin_headers):
    for name, brand, prices in [
        ("G430 Iron", "PING", [10000, 10000, 7900]),
        ("G440 Driver", "PING", [50000, 50000, 40000]),
        ("Pro V1", "Titleist", [5000, 5000, 4000]),
    ]:
        created = client.post(
            "/api/admin/products",
            headers=admin_headers,
            json={"name": name, "brand": brand, "category": "iron"},
        ).json()
        for price in prices:
            client.post(
                f"/api/admin/products/{created['id']}/prices", headers=admin_headers, json={"price": price}
            )

    brands = client.get("/api/brands").json()
    assert {"brand": "PING", "product_count": 2} in brands
    assert {"brand": "Titleist", "product_count": 1} in brands

    ping_products = client.get("/api/brands/PING").json()
    assert len(ping_products) == 2
    assert all(p["brand"] == "PING" for p in ping_products)

    filtered = client.get("/api/products?brand=Titleist").json()
    assert len(filtered) == 1
    assert filtered[0]["brand"] == "Titleist"

    assert client.get("/api/brands/Nonexistent").json() == []


def test_csv_import_endpoint(client, admin_headers):
    csv_content = (
        b"product_name,brand,category,model_number,price,product_url,image_url\n"
        b"Test Ball,Titleist,ball,PROV1,5000,,\n"
    )
    resp = client.post(
        "/api/admin/import/csv",
        headers=admin_headers,
        files={"file": ("prices.csv", csv_content, "text/csv")},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["created_products"] == 1
    assert body["errors"] == []


def test_delete_product(client, admin_headers):
    created = client.post(
        "/api/admin/products",
        headers=admin_headers,
        json={"name": "Temp", "brand": "X", "category": "ball"},
    ).json()
    resp = client.delete(f"/api/admin/products/{created['id']}", headers=admin_headers)
    assert resp.status_code == 204
    resp = client.get("/api/admin/products", headers=admin_headers)
    assert resp.json() == []


def test_run_update_endpoint(client, admin_headers):
    client.post(
        "/api/admin/products",
        headers=admin_headers,
        json={"name": "Ball A", "brand": "Titleist", "category": "ball", "initial_price": 5000},
    )
    resp = client.post("/api/admin/run-update", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["products_checked"] == 1


def test_fetch_rakuten_requires_app_id(client, admin_headers):
    resp = client.post("/api/admin/fetch-rakuten", headers=admin_headers)
    assert resp.status_code == 400


def test_delete_price_removes_bad_entry_and_recomputes(client, admin_headers):
    created = client.post(
        "/api/admin/products",
        headers=admin_headers,
        json={"name": "G430 Iron", "brand": "PING", "category": "iron", "initial_price": 60000},
    ).json()
    product_id = created["id"]

    bad = client.post(
        f"/api/admin/products/{product_id}/prices",
        headers=admin_headers,
        json={"price": 1100},
    ).json()
    assert bad["current_price"] == 1100

    prices = client.get(f"/api/admin/products/{product_id}/prices", headers=admin_headers).json()
    bad_entry = next(p for p in prices if p["price"] == 1100)

    resp = client.delete(f"/api/admin/prices/{bad_entry['id']}", headers=admin_headers)
    assert resp.status_code == 200
    fixed = resp.json()
    assert fixed["current_price"] == 60000
    assert fixed["lowest_price"] == 60000

    resp = client.delete(f"/api/admin/prices/{bad_entry['id']}", headers=admin_headers)
    assert resp.status_code == 404


def test_price_anomalies_scan_and_bulk_fix(client, admin_headers):
    created = client.post(
        "/api/admin/products",
        headers=admin_headers,
        json={"name": "G430 Iron", "brand": "PING", "category": "iron", "initial_price": 60000},
    ).json()
    product_id = created["id"]
    client.post(f"/api/admin/products/{product_id}/prices", headers=admin_headers, json={"price": 59000})
    client.post(f"/api/admin/products/{product_id}/prices", headers=admin_headers, json={"price": 1100})

    resp = client.get("/api/admin/price-anomalies", headers=admin_headers)
    assert resp.status_code == 200
    anomalies = resp.json()
    assert len(anomalies) == 1
    assert anomalies[0]["price"] == 1100

    resp = client.post("/api/admin/price-anomalies/fix", headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    product = client.get(f"/api/admin/products/{product_id}/prices", headers=admin_headers).json()
    assert all(p["price"] != 1100 for p in product)

    resp = client.get("/api/admin/price-anomalies", headers=admin_headers)
    assert resp.json() == []


def test_price_alert_subscribe_and_admin_visibility(client, admin_headers):
    created = client.post(
        "/api/admin/products",
        headers=admin_headers,
        json={"name": "G430 Iron", "brand": "PING", "category": "iron", "initial_price": 60000},
    ).json()
    slug = created["slug"]

    resp = client.post(f"/api/products/{slug}/alerts", json={"email": "buyer@example.com", "target_price": 50000})
    assert resp.status_code == 201
    alert = resp.json()
    assert alert["email"] == "buyer@example.com"
    assert alert["target_price"] == 50000
    assert alert["notified_at"] is None

    admin_alerts = client.get("/api/admin/price-alerts", headers=admin_headers).json()
    assert len(admin_alerts) == 1
    assert admin_alerts[0]["product_slug"] == slug
    assert admin_alerts[0]["current_price"] == 60000
    assert admin_alerts[0]["triggered"] is False  # 60000 > target 50000

    # Price drops below the target -> the admin view should flag it as triggered
    client.post(f"/api/admin/products/{created['id']}/prices", headers=admin_headers, json={"price": 45000})
    admin_alerts = client.get("/api/admin/price-alerts", headers=admin_headers).json()
    assert admin_alerts[0]["current_price"] == 45000
    assert admin_alerts[0]["triggered"] is True


def test_price_alert_rejects_invalid_email(client, admin_headers):
    created = client.post(
        "/api/admin/products",
        headers=admin_headers,
        json={"name": "G430 Iron", "brand": "PING", "category": "iron", "initial_price": 60000},
    ).json()
    resp = client.post(
        f"/api/products/{created['slug']}/alerts", json={"email": "not-an-email", "target_price": 50000}
    )
    assert resp.status_code == 422


def test_price_alert_unknown_product_404(client):
    resp = client.post("/api/products/no-such-slug/alerts", json={"email": "a@b.com", "target_price": 100})
    assert resp.status_code == 404
