import json


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

    stats = client.get("/api/brands/PING/price-stats").json()
    assert stats["brand"] == "PING"
    assert stats["tracked_count"] == 2
    # All three prices were recorded back-to-back with no real time gap, so
    # span is too short to count as a "reliable" trend (see
    # RELIABLE_TREND_MIN_HISTORY_DAYS) - test_crud.py covers the declining/
    # rising counting logic itself with realistic recorded_at spacing.
    assert stats["reliable_count"] == 0

    empty_stats = client.get("/api/brands/NoSuchBrand/price-stats").json()
    assert empty_stats["tracked_count"] == 0
    assert empty_stats["average_change_percent"] is None

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


def test_fetch_rakuten_survives_a_step_blowing_up(client, admin_headers, monkeypatch):
    """The daily job runs several independent steps in one request (price
    fetch, discovery, popularity sync, analysis, price alerts) - one of
    them raising an unexpected exception must not take the rest down with
    it (see routers/admin.py's fetch_rakuten), especially price alerts,
    which runs last and is the most user-facing part of the job."""
    monkeypatch.setenv("RAKUTEN_APP_ID", "test-app-id")
    monkeypatch.setenv("RAKUTEN_ACCESS_KEY", "test-access-key")
    from app.config import get_settings
    from app.routers import admin as admin_router

    get_settings.cache_clear()

    def _boom(db, on_progress=None):
        raise RuntimeError("boom: discovery is down")

    monkeypatch.setattr(admin_router.pipeline, "fetch_rakuten_prices", lambda db, on_progress=None: (0, 0))
    monkeypatch.setattr(admin_router.popularity, "sync_popularity_rankings", lambda db: (0, 0))
    monkeypatch.setattr(admin_router.discovery, "discover_new_products", _boom)

    try:
        resp = client.post("/api/admin/fetch-rakuten", headers=admin_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["products_discovered"] == 0
        assert body["candidates_considered"] == 0
        # Steps after the failed one still ran (price alerts is last).
        assert body["price_alerts_sent"] == 0
        assert body["price_alerts_skipped"] == 0

        logs = client.get("/api/admin/logs", headers=admin_headers).json()
        by_source = {log["source"]: log["message"] for log in logs}
        assert "discovery" in by_source
        # Confirms discover_new_products is actually the thing that raised
        # (rather than, say, an unrelated TypeError from a mismatched mock
        # signature elsewhere being silently caught and mistaken for this).
        assert "boom: discovery is down" in by_source["discovery"]
        assert "price_fetch" not in by_source
        # The summary row is only ever written at the very end of the
        # function, so its presence proves the job reached completion
        # despite the discovery step failing partway through.
        assert "daily_job" in by_source
    finally:
        get_settings.cache_clear()


def test_fetch_rakuten_survives_x_post_blowing_up(client, admin_headers, monkeypatch):
    """The X post step runs last, after price alerts - it failing must
    still let the job reach its final summary log rather than leaving the
    whole request half-done."""
    monkeypatch.setenv("RAKUTEN_APP_ID", "test-app-id")
    monkeypatch.setenv("RAKUTEN_ACCESS_KEY", "test-access-key")
    from app.config import get_settings
    from app.routers import admin as admin_router

    get_settings.cache_clear()

    monkeypatch.setattr(admin_router.pipeline, "fetch_rakuten_prices", lambda db, on_progress=None: (0, 0))
    monkeypatch.setattr(admin_router.popularity, "sync_popularity_rankings", lambda db: (0, 0))
    monkeypatch.setattr(admin_router.discovery, "discover_new_products", lambda db, on_progress=None: (0, 0))

    def _boom(db):
        raise RuntimeError("boom: X API is down")

    monkeypatch.setattr(admin_router.x_post, "post_daily_deals", _boom)

    try:
        resp = client.post("/api/admin/fetch-rakuten", headers=admin_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["x_posts_sent"] == 0
        assert body["x_posts_skipped"] == 0

        logs = client.get("/api/admin/logs", headers=admin_headers).json()
        by_source = {log["source"]: log["message"] for log in logs}
        assert "x_post" in by_source
        assert "boom: X API is down" in by_source["x_post"]
        assert "price_fetch" not in by_source
        assert "discovery" not in by_source
        assert "daily_job" in by_source
    finally:
        get_settings.cache_clear()


def test_fetch_rakuten_reports_live_progress_stages(client, admin_headers, monkeypatch):
    """fetch_rakuten drives app/progress.py's live dashboard (STEP13) -
    a full run should leave behind a "completed" snapshot naming every
    stage it actually ran, in order, each marked done."""
    monkeypatch.setenv("RAKUTEN_APP_ID", "test-app-id")
    monkeypatch.setenv("RAKUTEN_ACCESS_KEY", "test-access-key")
    from app.config import get_settings
    from app.routers import admin as admin_router

    get_settings.cache_clear()
    monkeypatch.setattr(admin_router.pipeline, "fetch_rakuten_prices", lambda db, on_progress=None: (2, 0))
    monkeypatch.setattr(admin_router.popularity, "sync_popularity_rankings", lambda db: (0, 0))
    monkeypatch.setattr(admin_router.discovery, "discover_new_products", lambda db, on_progress=None: (0, 0))

    try:
        resp = client.post("/api/admin/fetch-rakuten", headers=admin_headers)
        assert resp.status_code == 200

        from app import progress

        line = progress.get_snapshot_sse_line()
        assert line is not None
        event = json.loads(line[len("data: ") :].rstrip("\n"))
        assert event["job"] == "fetch_rakuten"
        assert event["status"] == "completed"
        assert event["stage"] is None  # no stage left "running" once finished
        stage_ids = [s["stage"] for s in event["stages"]]
        # yahoo_prices is absent (YAHOO_CLIENT_ID unset in tests) - every
        # other stage always runs.
        assert stage_ids == ["rakuten_prices", "discovery", "popularity", "analysis", "price_alerts", "x_post"]
        assert all(s["status"] == "done" for s in event["stages"])
    finally:
        get_settings.cache_clear()


def test_live_updates_requires_admin_auth(client):
    # /admin/live is a StreamingResponse whose body never ends on its own
    # (an open SSE connection) - only the auth-rejection path (401, a
    # normal non-streaming response returned before the stream is ever
    # created) can safely be exercised through TestClient's synchronous
    # request/response cycle; see app/progress.py's own tests plus
    # test_fetch_rakuten_reports_live_progress_stages above for coverage
    # of what actually gets streamed.
    resp = client.get("/api/admin/live")
    assert resp.status_code == 401


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


def test_contact_message_submit_and_admin_visibility(client, admin_headers):
    resp = client.post(
        "/api/contact",
        json={"name": "山田太郎", "email": "yamada@example.com", "message": "商品の登録について質問があります。"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "yamada@example.com"
    assert body["read_at"] is None

    admin_resp = client.get("/api/admin/contact-messages", headers=admin_headers)
    assert admin_resp.status_code == 200
    messages = admin_resp.json()
    assert len(messages) == 1
    assert messages[0]["message"] == "商品の登録について質問があります。"

    mark_resp = client.post(f"/api/admin/contact-messages/{body['id']}/read", headers=admin_headers)
    assert mark_resp.status_code == 200
    assert mark_resp.json()["read_at"] is not None


def test_contact_message_rejects_invalid_email(client):
    resp = client.post("/api/contact", json={"email": "not-an-email", "message": "hello"})
    assert resp.status_code == 422


def test_contact_message_requires_admin_token(client):
    resp = client.get("/api/admin/contact-messages")
    assert resp.status_code == 401


def test_analytics_top_pages_requires_ga4_configuration(client, admin_headers):
    resp = client.get("/api/admin/analytics/top-pages", headers=admin_headers)
    assert resp.status_code == 400


def test_discover_products_requires_rakuten_credentials(client, admin_headers):
    resp = client.post("/api/admin/discover-products", headers=admin_headers)
    assert resp.status_code == 400


def test_pending_product_hidden_from_public_but_visible_to_admin(client, admin_headers, db_session):
    """A pending (unreviewed) product must never appear on any public
    endpoint, but must be visible/manageable from the admin API so it can
    be approved."""
    created = client.post(
        "/api/admin/products",
        headers=admin_headers,
        json={"name": "Candidate Driver", "brand": "PING", "category": "driver", "initial_price": 68000},
    ).json()
    product_id = created["id"]
    slug = created["slug"]
    assert created["pending_review"] is False  # admin-created products publish normally

    # A single price point alone leaves buy_score "insufficient_data" (see
    # test_create_product_then_public_list_hides_insufficient_data) which
    # would hide it from public listing for an unrelated reason - add a
    # couple more so this test isolates the pending_review behavior itself.
    client.post(f"/api/admin/products/{product_id}/prices", headers=admin_headers, json={"price": 67000})
    client.post(f"/api/admin/products/{product_id}/prices", headers=admin_headers, json={"price": 66000})

    # Directly flip it to pending, as the auto-discovery pipeline would.
    from app import crud

    product = crud.get_product(db_session, product_id)
    product.pending_review = True
    db_session.commit()

    assert client.get("/api/products").json() == []
    assert client.get(f"/api/products/{slug}").status_code == 404
    assert client.get("/api/categories/driver").json() == []
    assert client.get("/api/brands").json() == []
    assert client.get("/api/brands/PING").json() == []

    pending = client.get("/api/admin/pending-products", headers=admin_headers).json()
    assert len(pending) == 1
    assert pending[0]["id"] == product_id

    approved = client.post(f"/api/admin/products/{product_id}/approve", headers=admin_headers).json()
    assert approved["pending_review"] is False

    public = client.get("/api/products").json()
    assert len(public) == 1
    assert public[0]["slug"] == slug

    assert client.get("/api/admin/pending-products", headers=admin_headers).json() == []


def test_send_price_alerts_requires_resend_configured(client, admin_headers, monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "")
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        resp = client.post("/api/admin/send-price-alerts", headers=admin_headers)
        assert resp.status_code == 400
    finally:
        get_settings.cache_clear()
