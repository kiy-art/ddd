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

    detail = client.get(f"/api/products/{updated['slug']}").json()
    assert len(detail["price_history"]) == 3

    by_category = client.get("/api/categories/iron").json()
    assert len(by_category) == 1


def test_unknown_category_404(client):
    resp = client.get("/api/categories/not-a-category")
    assert resp.status_code == 404


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
