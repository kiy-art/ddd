from app import crud, schemas


def _make_product(db_session, name, brand, category="driver"):
    return crud.create_product(
        db_session,
        schemas.ProductCreate(name=name, brand=brand, category=category, model_number=name),
    )


def test_track_click_without_product_id(client):
    resp = client.post(
        "/api/track/affiliate-click",
        json={"shop": "amazon", "placement": "product_detail_cta"},
    )
    assert resp.status_code == 204


def test_track_click_with_real_product(client, db_session):
    product = _make_product(db_session, "テスト用ドライバー", "TestBrand")

    resp = client.post(
        "/api/track/affiliate-click",
        json={
            "product_id": product.id,
            "category": "driver",
            "shop": "rakuten",
            "placement": "store_comparison",
        },
    )
    assert resp.status_code == 204

    summary = crud.get_affiliate_click_summary(db_session)
    assert summary.total == 1
    assert summary.by_shop[0].shop == "rakuten"
    assert summary.by_shop[0].count == 1
    assert summary.top_products[0].product_id == product.id
    assert summary.recent[0].product_name == "テスト用ドライバー"


def test_track_click_rejects_unknown_shop(client):
    resp = client.post(
        "/api/track/affiliate-click",
        json={"shop": "mercari", "placement": "product_detail_cta"},
    )
    assert resp.status_code == 422


def test_track_click_with_nonexistent_product_id_does_not_500(client, db_session):
    # A stale product_id from the browser (deleted product, mismatched
    # cache) must never turn a real click into a server error - it's
    # stored with product_id cleared instead (see crud.create_affiliate_click).
    resp = client.post(
        "/api/track/affiliate-click",
        json={"product_id": 999999, "shop": "amazon", "placement": "product_detail_cta"},
    )
    assert resp.status_code == 204

    summary = crud.get_affiliate_click_summary(db_session)
    assert summary.total == 1
    assert summary.top_products == []
    assert summary.recent[0].product_id is None


def test_affiliate_click_summary_requires_admin_auth(client):
    resp = client.get("/api/admin/affiliate-clicks/summary")
    assert resp.status_code in (401, 403)


def test_affiliate_click_summary_empty(client, admin_headers):
    resp = client.get("/api/admin/affiliate-clicks/summary", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert data["by_shop"] == []
    assert data["top_products"] == []
    assert data["recent"] == []


def test_affiliate_click_summary_aggregates_across_shops_and_products(client, db_session, admin_headers):
    p1 = _make_product(db_session, "商品A", "BrandA")
    p2 = _make_product(db_session, "商品B", "BrandB")

    clicks = [
        {"product_id": p1.id, "shop": "rakuten", "placement": "product_detail_cta"},
        {"product_id": p1.id, "shop": "rakuten", "placement": "store_comparison"},
        {"product_id": p1.id, "shop": "amazon", "placement": "store_comparison"},
        {"product_id": p2.id, "shop": "yahoo", "placement": "compare_table"},
    ]
    for payload in clicks:
        resp = client.post("/api/track/affiliate-click", json=payload)
        assert resp.status_code == 204

    resp = client.get("/api/admin/affiliate-clicks/summary", headers=admin_headers)
    data = resp.json()
    assert data["total"] == 4

    by_shop = {row["shop"]: row["count"] for row in data["by_shop"]}
    assert by_shop == {"rakuten": 2, "amazon": 1, "yahoo": 1}

    # p1 has 3 clicks (most-clicked), p2 has 1
    assert data["top_products"][0]["product_id"] == p1.id
    assert data["top_products"][0]["clicks"] == 3
    assert data["top_products"][1]["product_id"] == p2.id
    assert data["top_products"][1]["clicks"] == 1

    assert len(data["recent"]) == 4
