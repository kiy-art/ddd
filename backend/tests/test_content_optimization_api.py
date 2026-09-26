import datetime
import json

from app import content_optimizer, crud, models, schemas


def _make_product(db, name="G440 MAX ドライバー", brand="PING", category="driver", slug=None, **overrides):
    product = crud.create_product(
        db, schemas.ProductCreate(name=name, brand=brand, category=category, model_number=name, slug=slug, initial_price=60000)
    )
    for key, value in overrides.items():
        setattr(product, key, value)
    db.commit()
    return product


# --- GET /api/homepage/trending --------------------------------------------


def test_trending_endpoint_returns_empty_before_any_decision(client):
    resp = client.get("/api/homepage/trending")
    assert resp.status_code == 200
    assert resp.json() == {"decision_basis": None, "products": []}


def test_trending_endpoint_returns_real_decided_products(client, db_session):
    product = _make_product(db_session, buy_score="strong_buy", current_price=50000)
    db_session.add(
        models.AiOptimizationAction(
            action_type="reorder_homepage",
            target_path="/",
            decision_basis=f"直近7日間のクリック数上位: {product.name}（3件）",
            content_after=json.dumps({"product_ids": [product.id]}),
            status="applied",
        )
    )
    db_session.commit()

    resp = client.get("/api/homepage/trending")
    assert resp.status_code == 200
    data = resp.json()
    assert product.name in data["decision_basis"]
    assert len(data["products"]) == 1
    assert data["products"][0]["id"] == product.id


# --- GET /api/guides, /api/guides/{slug} ------------------------------------


def _make_guide_article(db, slug="xxio-driver-guide"):
    guide = models.GuideArticle(
        slug=slug,
        title="XXIOドライバー特集",
        description="ゼクシオのドライバーをまとめました。",
        published_at=datetime.date.today(),
        related_categories="driver",
        featured_kind="top_buy_signal",
        featured_category="driver",
        featured_heading="XXIOの注目商品",
        featured_limit=6,
        sections_json=json.dumps([{"heading": "このページの見方", "paragraphs": ["実データに基づく一覧です。"]}], ensure_ascii=False),
        source="ai_generated",
        based_on_query="ゼクシオ ドライバー",
    )
    db.add(guide)
    db.commit()
    return guide


def test_list_ai_guides_empty_by_default(client):
    resp = client.get("/api/guides")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_and_get_ai_guide(client, db_session):
    _make_guide_article(db_session)

    listed = client.get("/api/guides").json()
    assert len(listed) == 1
    assert listed[0]["slug"] == "xxio-driver-guide"
    assert listed[0]["related_categories"] == ["driver"]

    detail = client.get("/api/guides/xxio-driver-guide")
    assert detail.status_code == 200
    body = detail.json()
    assert body["title"] == "XXIOドライバー特集"
    assert body["sections"][0]["heading"] == "このページの見方"


def test_get_ai_guide_404_for_unknown_slug(client):
    resp = client.get("/api/guides/does-not-exist")
    assert resp.status_code == 404


# --- admin: run-content-optimization / optimization-actions / revert -------


def test_run_content_optimization_requires_admin_auth(client):
    resp = client.post("/api/admin/run-content-optimization")
    assert resp.status_code in (401, 403)


def test_run_content_optimization_endpoint_returns_shape(client, admin_headers, monkeypatch):
    monkeypatch.setattr(
        content_optimizer, "run_daily_optimization",
        lambda db: content_optimizer.OptimizationRunResult(
            ga4_available=False, search_console_available=False, actions_evaluated=0, actions=[]
        ),
    )
    resp = client.post("/api/admin/run-content-optimization", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json() == {
        "snapshot_captured": False,
        "actions_evaluated": 0,
        "actions_applied": 0,
        "actions": [],
    }


def test_run_content_optimization_endpoint_surfaces_real_error_message(client, admin_headers, monkeypatch):
    def _boom(db):
        raise RuntimeError("Search Console API error: User does not have sufficient permission for site")

    monkeypatch.setattr(content_optimizer, "run_daily_optimization", _boom)

    resp = client.post("/api/admin/run-content-optimization", headers=admin_headers)
    assert resp.status_code == 502
    assert "sufficient permission" in resp.json()["detail"]

    logs = client.get("/api/admin/logs", headers=admin_headers).json()
    assert any(log["source"] == "content_optimizer" for log in logs)


def test_list_optimization_actions_requires_admin_auth(client):
    resp = client.get("/api/admin/optimization-actions")
    assert resp.status_code in (401, 403)


def test_list_optimization_actions_returns_real_rows(client, admin_headers, db_session):
    product = _make_product(db_session)
    db_session.add(
        models.AiOptimizationAction(
            action_type="rewrite_product", target_path=f"/products/{product.slug}", product_id=product.id,
            decision_basis="CTRが低下", status="applied",
        )
    )
    db_session.commit()

    resp = client.get("/api/admin/optimization-actions", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["decision_basis"] == "CTRが低下"


def test_revert_optimization_action_restores_previous_content(client, admin_headers, db_session):
    product = _make_product(db_session, ai_title="新タイトル", ai_summary="新サマリー", ai_caution="新注意書き")
    action = models.AiOptimizationAction(
        action_type="rewrite_product", target_path=f"/products/{product.slug}", product_id=product.id,
        decision_basis="CTRが低下",
        content_before=json.dumps({"ai_title": "旧タイトル", "ai_summary": "旧サマリー", "ai_caution": "旧注意書き"}, ensure_ascii=False),
        content_after=json.dumps({"ai_title": "新タイトル", "ai_summary": "新サマリー", "ai_caution": "新注意書き"}, ensure_ascii=False),
        status="applied",
    )
    db_session.add(action)
    db_session.commit()
    product.ai_copy_source_action_id = action.id
    db_session.commit()

    resp = client.post(f"/api/admin/optimization-actions/{action.id}/revert", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "reverted"

    db_session.refresh(product)
    assert product.ai_title == "旧タイトル"
    assert product.ai_copy_source_action_id is None


def test_revert_optimization_action_404_for_unknown_id(client, admin_headers):
    resp = client.post("/api/admin/optimization-actions/999999/revert", headers=admin_headers)
    assert resp.status_code == 404


def test_revert_optimization_action_rejects_non_rewrite_action(client, admin_headers, db_session):
    action = models.AiOptimizationAction(
        action_type="reorder_homepage", target_path="/", decision_basis="x", status="applied",
    )
    db_session.add(action)
    db_session.commit()

    resp = client.post(f"/api/admin/optimization-actions/{action.id}/revert", headers=admin_headers)
    assert resp.status_code == 400


def test_revert_optimization_action_rejects_already_reverted(client, admin_headers, db_session):
    product = _make_product(db_session)
    action = models.AiOptimizationAction(
        action_type="rewrite_product", target_path=f"/products/{product.slug}", product_id=product.id,
        decision_basis="x", content_before=json.dumps({"ai_title": "a", "ai_summary": "b", "ai_caution": "c"}),
        status="applied", reverted_at=datetime.datetime.utcnow(),
    )
    db_session.add(action)
    db_session.commit()

    resp = client.post(f"/api/admin/optimization-actions/{action.id}/revert", headers=admin_headers)
    assert resp.status_code == 400


def test_improvement_opportunities_requires_admin_auth(client):
    resp = client.get("/api/admin/improvement-opportunities")
    assert resp.status_code in (401, 403)


def test_improvement_opportunities_returns_ranked_real_gaps(client, admin_headers, db_session):
    weak = _make_product(db_session, name="weak", slug="weak", current_price=60000)
    ref = _make_product(db_session, name="ref", slug="ref")
    today = datetime.date.today()
    for product, clicks in ((weak, 10), (ref, 80)):
        db_session.add(models.PageMetricsSnapshot(
            snapshot_date=today, path=f"/products/{product.slug}", product_id=product.id,
            search_impressions=1000, search_clicks=clicks, search_ctr=clicks / 1000, search_position=5.0,
        ))
    db_session.commit()

    resp = client.get("/api/admin/improvement-opportunities", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert [o["product_name"] for o in body] == ["weak"]
    assert body[0]["goal"] == "search_ctr"
    assert body[0]["target_path"] == "/products/weak"
