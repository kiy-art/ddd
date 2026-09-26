import datetime

from app import content_optimizer, content_rewriter, crud, models, schemas, search_console


def _make_product(db, name="G440 MAX ドライバー", brand="PING", category="driver", slug=None, **overrides):
    product = crud.create_product(
        db,
        schemas.ProductCreate(
            name=name, brand=brand, category=category, model_number=name, slug=slug or None, initial_price=60000
        ),
    )
    for key, value in overrides.items():
        setattr(product, key, value)
    db.commit()
    return product


def _snapshot(db, path, snapshot_date, product_id=None, **fields):
    row = models.PageMetricsSnapshot(snapshot_date=snapshot_date, path=path, product_id=product_id, **fields)
    db.add(row)
    db.commit()
    return row


# --- find_underperforming_products ---------------------------------------


def test_underperforming_requires_at_least_two_snapshots(db_session):
    product = _make_product(db_session)
    _snapshot(db_session, f"/products/{product.slug}", datetime.date.today(), product_id=product.id, pageviews=5)

    findings = content_optimizer.find_underperforming_products(db_session)
    assert findings == []


def test_underperforming_ignores_decline_below_threshold(db_session):
    product = _make_product(db_session)
    path = f"/products/{product.slug}"
    _snapshot(db_session, path, datetime.date.today() - datetime.timedelta(days=10), product_id=product.id, pageviews=100)
    _snapshot(db_session, path, datetime.date.today(), product_id=product.id, pageviews=90)  # only -10%

    assert content_optimizer.find_underperforming_products(db_session) == []


def test_underperforming_ignores_noise_below_baseline_floor(db_session):
    product = _make_product(db_session)
    path = f"/products/{product.slug}"
    # Real -80% decline, but baseline is tiny (below MIN_BASELINE_PAGEVIEWS) - noise, not a signal.
    _snapshot(db_session, path, datetime.date.today() - datetime.timedelta(days=10), product_id=product.id, pageviews=5)
    _snapshot(db_session, path, datetime.date.today(), product_id=product.id, pageviews=1)

    assert content_optimizer.find_underperforming_products(db_session) == []


def test_underperforming_flags_a_real_pageview_decline(db_session):
    product = _make_product(db_session)
    path = f"/products/{product.slug}"
    _snapshot(db_session, path, datetime.date.today() - datetime.timedelta(days=10), product_id=product.id, pageviews=100)
    _snapshot(db_session, path, datetime.date.today(), product_id=product.id, pageviews=60)  # -40%

    findings = content_optimizer.find_underperforming_products(db_session)
    assert len(findings) == 1
    assert findings[0].product.id == product.id
    assert "40%" in findings[0].decision_basis


def test_underperforming_prefers_search_ctr_over_pageviews_when_both_present(db_session):
    product = _make_product(db_session)
    path = f"/products/{product.slug}"
    _snapshot(
        db_session, path, datetime.date.today() - datetime.timedelta(days=10), product_id=product.id,
        pageviews=100, search_ctr=0.05, search_impressions=200,
    )
    _snapshot(
        db_session, path, datetime.date.today(), product_id=product.id,
        pageviews=100, search_ctr=0.02, search_impressions=200,  # CTR -60%, pageviews flat
    )

    findings = content_optimizer.find_underperforming_products(db_session)
    assert len(findings) == 1
    assert "検索クリック率" in findings[0].decision_basis


def test_underperforming_respects_rewrite_cooldown(db_session):
    product = _make_product(db_session)
    path = f"/products/{product.slug}"
    _snapshot(db_session, path, datetime.date.today() - datetime.timedelta(days=10), product_id=product.id, pageviews=100)
    _snapshot(db_session, path, datetime.date.today(), product_id=product.id, pageviews=50)

    db_session.add(
        models.AiOptimizationAction(
            action_type="rewrite_product", target_path=path, product_id=product.id,
            decision_basis="以前の判断", status="applied",
        )
    )
    db_session.commit()

    assert content_optimizer.find_underperforming_products(db_session) == []


# --- select_trending_products ---------------------------------------------


def test_trending_returns_empty_with_no_clicks(db_session):
    assert content_optimizer.select_trending_products(db_session) == []


def test_trending_ranks_by_real_click_count(db_session):
    popular = _make_product(db_session, name="popular", slug="popular")
    quiet = _make_product(db_session, name="quiet", slug="quiet")
    for _ in range(3):
        crud.create_affiliate_click(
            db_session, schemas.AffiliateClickCreate(product_id=popular.id, shop="amazon", placement="product_detail_cta")
        )
    crud.create_affiliate_click(
        db_session, schemas.AffiliateClickCreate(product_id=quiet.id, shop="amazon", placement="product_detail_cta")
    )

    ranked = content_optimizer.select_trending_products(db_session)
    assert [p.id for p, _ in ranked] == [popular.id, quiet.id]
    assert dict((p.id, c) for p, c in ranked) == {popular.id: 3, quiet.id: 1}


# --- find_new_guide_opportunities ------------------------------------------


def test_new_guide_opportunities_empty_when_search_console_not_configured(db_session, monkeypatch):
    monkeypatch.setattr(
        search_console, "get_top_queries", lambda **kwargs: (_ for _ in ()).throw(search_console.SearchConsoleNotConfigured())
    )
    assert content_optimizer.find_new_guide_opportunities(db_session) == []


def test_new_guide_opportunities_requires_enough_real_matching_products(db_session, monkeypatch):
    _make_product(db_session, name="p1", slug="p1", brand="XXIO", category="driver")
    _make_product(db_session, name="p2", slug="p2", brand="XXIO", category="driver")
    # Only 2 XXIO products - below NEW_GUIDE_MIN_PRODUCTS (3).
    monkeypatch.setattr(
        search_console,
        "get_top_queries",
        lambda **kwargs: [search_console.QueryPerformance(query="ゼクシオ ドライバー", clicks=5, impressions=100, ctr=0.05, position=5.0)],
    )
    assert content_optimizer.find_new_guide_opportunities(db_session) == []


def test_new_guide_opportunities_matches_brand_and_dedupes_by_query(db_session, monkeypatch):
    for i in range(3):
        _make_product(db_session, name=f"XXIO p{i}", slug=f"xxio-p{i}", brand="XXIO", category="driver")

    monkeypatch.setattr(
        search_console,
        "get_top_queries",
        lambda **kwargs: [search_console.QueryPerformance(query="ゼクシオ ドライバー", clicks=5, impressions=100, ctr=0.05, position=5.0)],
    )

    opportunities = content_optimizer.find_new_guide_opportunities(db_session)
    assert len(opportunities) == 1
    assert opportunities[0].brand == "XXIO"
    assert opportunities[0].category == "driver"
    assert len(opportunities[0].products) == 3

    db_session.add(models.GuideArticle(
        slug="xxio-driver-guide", title="t", description="d", published_at=datetime.date.today(),
        sections_json="[]", source="ai_generated", based_on_query="ゼクシオ ドライバー",
    ))
    db_session.commit()
    assert content_optimizer.find_new_guide_opportunities(db_session) == []


# --- run_daily_optimization -------------------------------------------------


def test_run_daily_optimization_applies_homepage_reorder_from_real_clicks(db_session, monkeypatch):
    monkeypatch.setattr(content_optimizer.content_metrics, "capture_daily_snapshot", lambda db: content_optimizer.content_metrics.SnapshotCaptureResult(False, False, 0))
    product = _make_product(db_session)
    crud.create_affiliate_click(
        db_session, schemas.AffiliateClickCreate(product_id=product.id, shop="amazon", placement="product_detail_cta")
    )

    result = content_optimizer.run_daily_optimization(db_session)
    reorder_actions = [a for a in result.actions if a.action_type == "reorder_homepage"]
    assert len(reorder_actions) == 1
    assert product.name in reorder_actions[0].decision_basis


def test_run_daily_optimization_applies_a_rewrite_and_persists_it(db_session, monkeypatch):
    monkeypatch.setattr(content_optimizer.content_metrics, "capture_daily_snapshot", lambda db: content_optimizer.content_metrics.SnapshotCaptureResult(False, False, 0))
    product = _make_product(db_session)
    path = f"/products/{product.slug}"
    _snapshot(db_session, path, datetime.date.today() - datetime.timedelta(days=10), product_id=product.id, pageviews=100)
    _snapshot(db_session, path, datetime.date.today(), product_id=product.id, pageviews=50)

    monkeypatch.setattr(
        content_rewriter,
        "rewrite_product_copy",
        lambda product, reason: content_rewriter.RewrittenProductCopy(title="新タイトル", summary="新サマリー", caution="価格は変動する可能性があります。"),
    )

    result = content_optimizer.run_daily_optimization(db_session)
    rewrite_actions = [a for a in result.actions if a.action_type == "rewrite_product"]
    assert len(rewrite_actions) == 1
    assert rewrite_actions[0].status == "applied"

    db_session.refresh(product)
    assert product.ai_title == "新タイトル"


def test_run_daily_optimization_logs_failed_rewrite_without_crashing(db_session, monkeypatch):
    monkeypatch.setattr(content_optimizer.content_metrics, "capture_daily_snapshot", lambda db: content_optimizer.content_metrics.SnapshotCaptureResult(False, False, 0))
    product = _make_product(db_session)
    path = f"/products/{product.slug}"
    _snapshot(db_session, path, datetime.date.today() - datetime.timedelta(days=10), product_id=product.id, pageviews=100)
    _snapshot(db_session, path, datetime.date.today(), product_id=product.id, pageviews=50)

    def _boom(product, reason):
        raise RuntimeError("Claude API error")

    monkeypatch.setattr(content_rewriter, "rewrite_product_copy", _boom)

    result = content_optimizer.run_daily_optimization(db_session)
    rewrite_actions = [a for a in result.actions if a.action_type == "rewrite_product"]
    assert len(rewrite_actions) == 1
    assert rewrite_actions[0].status == "failed"

    logs = crud.list_error_logs(db_session)
    assert any(log.source == "content_optimizer" for log in logs)


def test_run_daily_optimization_respects_daily_action_cap(db_session, monkeypatch):
    monkeypatch.setattr(content_optimizer.content_metrics, "capture_daily_snapshot", lambda db: content_optimizer.content_metrics.SnapshotCaptureResult(False, False, 0))
    monkeypatch.setattr(content_optimizer, "DAILY_ACTION_CAP", 1)

    products = []
    for i in range(3):
        p = _make_product(db_session, name=f"underperformer {i}", slug=f"underperformer-{i}")
        products.append(p)
        path = f"/products/{p.slug}"
        _snapshot(db_session, path, datetime.date.today() - datetime.timedelta(days=10), product_id=p.id, pageviews=100)
        _snapshot(db_session, path, datetime.date.today(), product_id=p.id, pageviews=50)

    monkeypatch.setattr(
        content_rewriter,
        "rewrite_product_copy",
        lambda product, reason: content_rewriter.RewrittenProductCopy(title="t", summary="s", caution="c"),
    )

    result = content_optimizer.run_daily_optimization(db_session)
    rewrite_actions = [a for a in result.actions if a.action_type == "rewrite_product"]
    assert len(rewrite_actions) == 1


# --- evaluate_past_actions ---------------------------------------------------


def test_evaluate_past_actions_skips_actions_too_young_to_judge(db_session):
    product = _make_product(db_session)
    action = models.AiOptimizationAction(
        action_type="rewrite_product", target_path=f"/products/{product.slug}", product_id=product.id,
        decision_basis="x", status="applied",
    )
    db_session.add(action)
    db_session.commit()

    evaluated = content_optimizer.evaluate_past_actions(db_session)
    assert evaluated == 0
    db_session.refresh(action)
    assert action.effect_evaluated_at is None


def test_evaluate_past_actions_detects_improvement(db_session):
    product = _make_product(db_session)
    path = f"/products/{product.slug}"
    old_created_at = datetime.datetime.utcnow() - datetime.timedelta(days=10)

    action = models.AiOptimizationAction(
        action_type="rewrite_product", target_path=path, product_id=product.id,
        decision_basis="x", status="applied",
    )
    db_session.add(action)
    db_session.commit()
    action.created_at = old_created_at
    db_session.commit()

    _snapshot(db_session, path, old_created_at.date(), product_id=product.id, pageviews=50)
    _snapshot(db_session, path, datetime.date.today(), product_id=product.id, pageviews=100)  # +100%

    evaluated = content_optimizer.evaluate_past_actions(db_session)
    assert evaluated == 1
    db_session.refresh(action)
    assert action.effect_verdict == "improved"
    assert "50件" in action.effect_summary and "100件" in action.effect_summary


def test_evaluate_past_actions_detects_no_real_data_yet_and_retries_later(db_session):
    product = _make_product(db_session)
    path = f"/products/{product.slug}"
    old_created_at = datetime.datetime.utcnow() - datetime.timedelta(days=10)

    action = models.AiOptimizationAction(
        action_type="rewrite_product", target_path=path, product_id=product.id,
        decision_basis="x", status="applied",
    )
    db_session.add(action)
    db_session.commit()
    action.created_at = old_created_at
    db_session.commit()
    # No snapshots at all - nothing to compare yet.

    evaluated = content_optimizer.evaluate_past_actions(db_session)
    assert evaluated == 0
    db_session.refresh(action)
    assert action.effect_evaluated_at is None
