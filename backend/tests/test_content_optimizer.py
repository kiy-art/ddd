import datetime
import json

import pytest

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


# --- find_improvement_opportunities: trend-decline detector ------------


def test_underperforming_requires_at_least_two_snapshots(db_session):
    product = _make_product(db_session)
    _snapshot(db_session, f"/products/{product.slug}", datetime.date.today(), product_id=product.id, pageviews=5)

    findings = content_optimizer.find_improvement_opportunities(db_session)
    assert findings == []


def test_underperforming_ignores_decline_below_threshold(db_session):
    product = _make_product(db_session)
    path = f"/products/{product.slug}"
    _snapshot(db_session, path, datetime.date.today() - datetime.timedelta(days=10), product_id=product.id, pageviews=100)
    _snapshot(db_session, path, datetime.date.today(), product_id=product.id, pageviews=90)  # only -10%

    assert content_optimizer.find_improvement_opportunities(db_session) == []


def test_underperforming_ignores_noise_below_baseline_floor(db_session):
    product = _make_product(db_session)
    path = f"/products/{product.slug}"
    # Real -80% decline, but baseline is tiny (below MIN_BASELINE_PAGEVIEWS) - noise, not a signal.
    _snapshot(db_session, path, datetime.date.today() - datetime.timedelta(days=10), product_id=product.id, pageviews=5)
    _snapshot(db_session, path, datetime.date.today(), product_id=product.id, pageviews=1)

    assert content_optimizer.find_improvement_opportunities(db_session) == []


def test_underperforming_flags_a_real_pageview_decline(db_session):
    product = _make_product(db_session)
    path = f"/products/{product.slug}"
    _snapshot(db_session, path, datetime.date.today() - datetime.timedelta(days=10), product_id=product.id, pageviews=100)
    _snapshot(db_session, path, datetime.date.today(), product_id=product.id, pageviews=60)  # -40%

    findings = content_optimizer.find_improvement_opportunities(db_session)
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

    findings = content_optimizer.find_improvement_opportunities(db_session)
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

    assert content_optimizer.find_improvement_opportunities(db_session) == []


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
        lambda product, reason, **kwargs: content_rewriter.RewrittenProductCopy(title="新タイトル", summary="新サマリー", caution="価格は変動する可能性があります。"),
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

    def _boom(product, reason, **kwargs):
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
        lambda product, reason, **kwargs: content_rewriter.RewrittenProductCopy(title="t", summary="s", caution="c"),
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

    evaluated = content_optimizer.evaluate_past_actions(db_session).evaluated
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
    product.ai_copy_source_action_id = action.id
    db_session.commit()

    _snapshot(db_session, path, old_created_at.date(), product_id=product.id, pageviews=50)
    _snapshot(db_session, path, datetime.date.today(), product_id=product.id, pageviews=100)  # +100%

    evaluated = content_optimizer.evaluate_past_actions(db_session).evaluated
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
    product.ai_copy_source_action_id = action.id
    db_session.commit()
    # No snapshots at all - nothing to compare yet.

    evaluated = content_optimizer.evaluate_past_actions(db_session).evaluated
    assert evaluated == 0
    db_session.refresh(action)
    assert action.effect_evaluated_at is None


def test_evaluate_past_actions_marks_inconclusive_when_copy_was_replaced(db_session):
    product = _make_product(db_session)
    path = f"/products/{product.slug}"
    old_created_at = datetime.datetime.utcnow() - datetime.timedelta(days=10)
    action = models.AiOptimizationAction(
        action_type="rewrite_product", target_path=path, product_id=product.id, decision_basis="x", status="applied",
    )
    db_session.add(action)
    db_session.commit()
    action.created_at = old_created_at
    product.ai_copy_source_action_id = None  # routine regeneration replaced the optimizer's copy
    db_session.commit()
    _snapshot(db_session, path, old_created_at.date(), product_id=product.id, pageviews=50)
    _snapshot(db_session, path, datetime.date.today(), product_id=product.id, pageviews=100)

    assert content_optimizer.evaluate_past_actions(db_session).evaluated == 1
    db_session.refresh(action)
    assert action.effect_verdict == "inconclusive"


# --- STEP43: revenue-proxy opportunity scoring -------------------------------


def _click(db, product_id, n=1):
    for _ in range(n):
        crud.create_affiliate_click(
            db, schemas.AffiliateClickCreate(product_id=product_id, shop="amazon", placement="product_detail_cta")
        )


def test_search_ctr_gap_is_found_from_a_single_snapshot_vs_site_average(db_session):
    weak = _make_product(db_session, name="weak", slug="weak")
    strong = _make_product(db_session, name="strong", slug="strong")
    today = datetime.date.today()
    _snapshot(db_session, "/products/weak", today, product_id=weak.id,
              search_impressions=1000, search_clicks=10, search_ctr=0.01, search_position=6.0)
    _snapshot(db_session, "/products/strong", today, product_id=strong.id,
              search_impressions=1000, search_clicks=70, search_ctr=0.07, search_position=4.0)

    opps = content_optimizer.find_improvement_opportunities(db_session)
    assert [o.product.id for o in opps] == [weak.id]
    assert opps[0].goal == content_optimizer.GOAL_SEARCH_CTR
    assert "商品ページ平均4.0%" in opps[0].decision_basis


def test_search_gap_ignores_pages_beyond_page_two_or_with_too_few_impressions(db_session):
    far = _make_product(db_session, name="far", slug="far")
    tiny = _make_product(db_session, name="tiny", slug="tiny")
    ref = _make_product(db_session, name="ref", slug="ref")
    today = datetime.date.today()
    _snapshot(db_session, "/products/far", today, product_id=far.id,
              search_impressions=1000, search_clicks=5, search_ctr=0.005, search_position=35.0)
    _snapshot(db_session, "/products/tiny", today, product_id=tiny.id,
              search_impressions=20, search_clicks=0, search_ctr=0.0, search_position=5.0)
    _snapshot(db_session, "/products/ref", today, product_id=ref.id,
              search_impressions=1000, search_clicks=80, search_ctr=0.08, search_position=3.0)

    assert content_optimizer.find_improvement_opportunities(db_session) == []


def test_on_page_conversion_gap_uses_real_shop_clicks(db_session):
    leaky = _make_product(db_session, name="leaky", slug="leaky")
    good = _make_product(db_session, name="good", slug="good")
    today = datetime.date.today()
    _snapshot(db_session, "/products/leaky", today, product_id=leaky.id, pageviews=200)
    _snapshot(db_session, "/products/good", today, product_id=good.id, pageviews=200)
    _click(db_session, leaky.id, 1)
    _click(db_session, good.id, 20)

    opps = content_optimizer.find_improvement_opportunities(db_session)
    assert [o.product.id for o in opps] == [leaky.id]
    assert opps[0].goal == content_optimizer.GOAL_ON_PAGE_CONVERSION
    assert opps[0].shop_click_rate_known is True


def test_priority_weights_the_same_gap_by_price_as_a_commission_proxy(db_session):
    cheap = _make_product(db_session, name="cheap ball", slug="cheap", category="ball", current_price=5000)
    pricey = _make_product(db_session, name="pricey driver", slug="pricey", current_price=80000)
    ref = _make_product(db_session, name="ref", slug="ref")
    today = datetime.date.today()
    for p in (cheap, pricey):
        _snapshot(db_session, f"/products/{p.slug}", today, product_id=p.id,
                  search_impressions=1000, search_clicks=10, search_ctr=0.01, search_position=5.0)
    _snapshot(db_session, "/products/ref", today, product_id=ref.id,
              search_impressions=1000, search_clicks=90, search_ctr=0.09, search_position=2.0)

    opps = content_optimizer.find_improvement_opportunities(db_session)
    assert [o.product.id for o in opps] == [pricey.id, cheap.id]
    assert opps[0].priority_score == pytest.approx(opps[1].priority_score * 16, rel=1e-4)


def test_run_daily_optimization_spends_the_cap_on_the_highest_priority_first(db_session, monkeypatch):
    monkeypatch.setattr(content_optimizer.content_metrics, "capture_daily_snapshot", lambda db: content_optimizer.content_metrics.SnapshotCaptureResult(False, False, 0))
    monkeypatch.setattr(content_optimizer, "DAILY_ACTION_CAP", 1)
    monkeypatch.setattr(content_optimizer, "_real_queries_for", lambda db, product: [])
    cheap = _make_product(db_session, name="cheap ball", slug="cheap", category="ball", current_price=5000)
    pricey = _make_product(db_session, name="pricey driver", slug="pricey", current_price=80000)
    ref = _make_product(db_session, name="ref", slug="ref")
    today = datetime.date.today()
    for p in (cheap, pricey):
        _snapshot(db_session, f"/products/{p.slug}", today, product_id=p.id,
                  search_impressions=1000, search_clicks=10, search_ctr=0.01, search_position=5.0)
    _snapshot(db_session, "/products/ref", today, product_id=ref.id,
              search_impressions=1000, search_clicks=90, search_ctr=0.09, search_position=2.0)

    calls = []

    def _rewrite(product, reason, goal=None, search_queries=None):
        calls.append((product.id, goal))
        return content_rewriter.RewrittenProductCopy(title="t", summary="s", caution="c")

    monkeypatch.setattr(content_rewriter, "rewrite_product_copy", _rewrite)

    content_optimizer.run_daily_optimization(db_session)
    assert calls == [(pricey.id, content_optimizer.GOAL_SEARCH_CTR)]
    db_session.refresh(pricey)
    assert pricey.ai_copy_source_action_id is not None


# --- STEP44: auto-revert of rewrites measured as "worse" ---------------------


def _aged_rewrite(db, product, content_before=None, days_ago=10):
    action = models.AiOptimizationAction(
        action_type="rewrite_product", target_path=f"/products/{product.slug}", product_id=product.id,
        decision_basis="x", status="applied",
        content_before=json.dumps(
            content_before or {"ai_title": "旧タイトル", "ai_summary": "旧サマリー", "ai_caution": "旧注意書き"},
            ensure_ascii=False,
        ),
    )
    db.add(action)
    db.commit()
    action.created_at = datetime.datetime.utcnow() - datetime.timedelta(days=days_ago)
    product.ai_copy_source_action_id = action.id
    product.ai_title = "最適化タイトル"
    product.ai_content_hash = "optimized-hash"
    db.commit()
    return action


def test_worse_rewrite_on_sufficient_sample_is_auto_reverted_and_regenerated(db_session):
    product = _make_product(db_session)
    path = f"/products/{product.slug}"
    action = _aged_rewrite(db_session, product)
    _snapshot(db_session, path, action.created_at.date(), product_id=product.id, pageviews=50)
    _snapshot(db_session, path, datetime.date.today(), product_id=product.id, pageviews=20)  # -60%

    result = content_optimizer.evaluate_past_actions(db_session)
    assert result.evaluated == 1
    assert [a.id for a in result.auto_reverted] == [action.id]

    db_session.refresh(action)
    db_session.refresh(product)
    assert action.effect_verdict == "worse"
    assert action.status == "reverted"
    assert action.revert_reason == "auto_worse"
    assert "自動で元に戻し" in action.effect_summary
    assert "50件" in action.effect_summary and "20件" in action.effect_summary
    assert product.ai_copy_source_action_id is None
    # Regenerated from today's real data - neither the optimizer's copy nor
    # the possibly-stale content_before is left on the page.
    assert product.ai_title not in ("最適化タイトル", "旧タイトル")
    assert product.ai_content_hash not in (None, "optimized-hash")

    logs = crud.list_error_logs(db_session)
    assert any(log.level == "warning" and "自動差し戻し" in log.message for log in logs)


def test_worse_search_ctr_rewrite_on_sufficient_impressions_is_auto_reverted(db_session):
    product = _make_product(db_session)
    path = f"/products/{product.slug}"
    action = _aged_rewrite(db_session, product)
    _snapshot(db_session, path, action.created_at.date(), product_id=product.id,
              search_impressions=500, search_clicks=25, search_ctr=0.05)
    _snapshot(db_session, path, datetime.date.today(), product_id=product.id,
              search_impressions=500, search_clicks=10, search_ctr=0.02)

    result = content_optimizer.evaluate_past_actions(db_session)
    assert len(result.auto_reverted) == 1
    db_session.refresh(action)
    assert action.status == "reverted"
    assert "検索クリック率" in action.effect_summary


def test_worse_rewrite_on_thin_sample_is_recorded_but_not_auto_reverted(db_session):
    product = _make_product(db_session)
    path = f"/products/{product.slug}"
    action = _aged_rewrite(db_session, product)
    # 5 -> 2 pageviews is -60%, but 5 is below AUTO_REVERT_MIN_PAGEVIEWS.
    _snapshot(db_session, path, action.created_at.date(), product_id=product.id, pageviews=5)
    _snapshot(db_session, path, datetime.date.today(), product_id=product.id, pageviews=2)

    result = content_optimizer.evaluate_past_actions(db_session)
    assert result.evaluated == 1
    assert result.auto_reverted == []

    db_session.refresh(action)
    db_session.refresh(product)
    assert action.effect_verdict == "worse"
    assert action.status == "applied"
    assert "サンプル数が少ない" in action.effect_summary
    assert product.ai_title == "最適化タイトル"


def test_improved_rewrite_is_never_auto_reverted(db_session):
    product = _make_product(db_session)
    path = f"/products/{product.slug}"
    action = _aged_rewrite(db_session, product)
    _snapshot(db_session, path, action.created_at.date(), product_id=product.id, pageviews=50)
    _snapshot(db_session, path, datetime.date.today(), product_id=product.id, pageviews=100)

    result = content_optimizer.evaluate_past_actions(db_session)
    assert result.auto_reverted == []
    db_session.refresh(action)
    assert action.status == "applied"


def test_auto_revert_keeps_the_revert_when_regeneration_fails(db_session, monkeypatch):
    product = _make_product(db_session)
    path = f"/products/{product.slug}"
    action = _aged_rewrite(db_session, product)
    _snapshot(db_session, path, action.created_at.date(), product_id=product.id, pageviews=50)
    _snapshot(db_session, path, datetime.date.today(), product_id=product.id, pageviews=20)

    def _boom(db, product):
        raise RuntimeError("regeneration exploded")

    monkeypatch.setattr(content_optimizer.pipeline, "sync_product_analysis", _boom)

    result = content_optimizer.evaluate_past_actions(db_session)
    assert len(result.auto_reverted) == 1
    db_session.refresh(action)
    db_session.refresh(product)
    assert action.status == "reverted"
    assert "次回の日次更新で再試行" in action.effect_summary
    assert product.ai_title == "旧タイトル"
    assert product.ai_content_hash is None  # next daily sync regenerates
    assert any("regeneration exploded" in log.message for log in crud.list_error_logs(db_session))


def test_run_daily_optimization_deducts_auto_reverts_from_the_cap_and_skips_the_reverted_product(db_session, monkeypatch):
    monkeypatch.setattr(content_optimizer.content_metrics, "capture_daily_snapshot", lambda db: content_optimizer.content_metrics.SnapshotCaptureResult(False, False, 0))
    monkeypatch.setattr(content_optimizer, "DAILY_ACTION_CAP", 2)

    reverted_product = _make_product(db_session, name="reverted", slug="reverted")
    action = _aged_rewrite(db_session, reverted_product)
    _snapshot(db_session, "/products/reverted", action.created_at.date(), product_id=reverted_product.id, pageviews=100)
    _snapshot(db_session, "/products/reverted", datetime.date.today(), product_id=reverted_product.id, pageviews=40)

    for i in range(3):
        p = _make_product(db_session, name=f"underperformer {i}", slug=f"underperformer-{i}")
        _snapshot(db_session, f"/products/{p.slug}", datetime.date.today() - datetime.timedelta(days=10), product_id=p.id, pageviews=100)
        _snapshot(db_session, f"/products/{p.slug}", datetime.date.today(), product_id=p.id, pageviews=50)

    monkeypatch.setattr(
        content_rewriter,
        "rewrite_product_copy",
        lambda product, reason, **kwargs: content_rewriter.RewrittenProductCopy(title="t", summary="s", caution="c"),
    )

    result = content_optimizer.run_daily_optimization(db_session)
    assert [a.id for a in result.actions_auto_reverted] == [action.id]
    rewrite_actions = [a for a in result.actions if a.action_type == "rewrite_product"]
    assert len(rewrite_actions) == 1  # cap 2 minus 1 auto-revert regeneration
    assert all(a.product_id != reverted_product.id for a in rewrite_actions)
