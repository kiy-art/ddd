"""STEP68: search-intent <title> retitles from real Search Console queries."""

import datetime
import json

from app import content_optimizer, content_rewriter, crud, models, schemas, seo_intent


def _q(query, impressions):
    return {"query": query, "clicks": 0, "impressions": impressions, "ctr": 0.0, "position": 5.0}


# --- seo_intent ---------------------------------------------------------------


def test_queries_are_read_as_timing_spec_or_price():
    assert seo_intent.classify_query("g440 max 買い時") == "timing"
    assert seo_intent.classify_query("G440 価格推移") == "timing"  # specific beats plain "価格"
    assert seo_intent.classify_query("qi35 ロフト 違い") == "spec"
    assert seo_intent.classify_query("ステルス2 最安値") == "price"
    assert seo_intent.classify_query("pingドライバー") is None


def test_unserved_queries_never_choose_a_title():
    assert seo_intent.classify_query("g440 中古") is None
    assert seo_intent.classify_query("g440 価格 口コミ") is None  # the page has no reviews
    intent, _ = seo_intent.dominant_intent([_q("g440 中古 安い", 500), _q("g440 レビュー", 300)])
    assert intent is None


def test_the_leading_intent_needs_a_clear_share_and_enough_impressions():
    intent, totals = seo_intent.dominant_intent([_q("g440 買い時", 60), _q("g440 最安値", 30), _q("g440", 10)])
    assert intent == "timing"
    assert totals == {"timing": 60, "price": 30}
    # Too few impressions to act on.
    assert seo_intent.dominant_intent([_q("g440 買い時", 10)])[0] is None
    # No intent reaches 40% of the served impressions.
    assert seo_intent.dominant_intent([_q("g440 買い時", 30), _q("g440 最安値", 30), _q("g440", 40)])[0] is None


# --- content_optimizer retitle --------------------------------------------------


def _product(db, slug, price=60000):
    p = crud.create_product(db, schemas.ProductCreate(name=f"{slug} ドライバー", brand="PING", category="driver", initial_price=price))
    p.slug = slug
    db.commit()
    return p


def _ctr_gap_setup(db):
    weak = _product(db, "weak")
    ref = _product(db, "ref")
    today = datetime.date.today()
    for product, ctr, pos in ((weak, 0.01, 6.0), (ref, 0.07, 4.0)):
        db.add(models.PageMetricsSnapshot(
            snapshot_date=today, path=f"/products/{product.slug}", product_id=product.id,
            search_impressions=1000, search_clicks=int(1000 * ctr), search_ctr=ctr, search_position=pos,
        ))
    db.commit()
    return weak


def _quiet_run(monkeypatch, queries):
    monkeypatch.setattr(
        content_optimizer.content_metrics, "capture_daily_snapshot",
        lambda db: content_optimizer.content_metrics.SnapshotCaptureResult(False, False, 0),
    )
    monkeypatch.setattr(content_optimizer, "_real_queries_for", lambda db, product: queries)
    monkeypatch.setattr(
        content_rewriter, "rewrite_product_copy",
        lambda product, reason, goal=None, search_queries=None: content_rewriter.RewrittenProductCopy(title="t", summary="s", caution="c"),
    )


def test_a_search_ctr_gap_retitles_the_page_to_its_real_search_intent(db_session, monkeypatch):
    weak = _ctr_gap_setup(db_session)
    _quiet_run(monkeypatch, [_q("weak 買い時", 400), _q("weak 最安値", 100)])

    result = content_optimizer.run_daily_optimization(db_session)

    db_session.refresh(weak)
    assert weak.seo_title_intent == "timing"
    retitles = [a for a in result.actions if a.action_type == "retitle_product"]
    assert len(retitles) == 1
    assert json.loads(retitles[0].content_before) == {"seo_title_intent": None}
    assert json.loads(retitles[0].content_after)["seo_title_intent"] == "timing"
    assert "timing 400回" in retitles[0].decision_basis


def test_no_retitle_without_a_clear_intent_or_when_already_matching(db_session, monkeypatch):
    weak = _ctr_gap_setup(db_session)
    # "price" is already the default title's intent - nothing to change.
    _quiet_run(monkeypatch, [_q("weak 最安値", 400)])
    result = content_optimizer.run_daily_optimization(db_session)
    assert not [a for a in result.actions if a.action_type == "retitle_product"]
    db_session.refresh(weak)
    assert weak.seo_title_intent is None


def test_a_retitle_can_be_reverted_and_is_not_repeated_within_the_cooldown(db_session, monkeypatch, client, admin_headers):
    weak = _ctr_gap_setup(db_session)
    _quiet_run(monkeypatch, [_q("weak ロフト 比較", 300)])
    action = next(a for a in content_optimizer.run_daily_optimization(db_session).actions if a.action_type == "retitle_product")
    db_session.refresh(weak)
    assert weak.seo_title_intent == "spec"

    # Within the cooldown the same page isn't retitled again.
    opportunity = content_optimizer.ImprovementOpportunity(
        product=weak, goal=content_optimizer.GOAL_SEARCH_CTR, decision_basis="again",
        est_extra_shop_clicks=1.0, priority_score=1.0, shop_click_rate_known=False,
    )
    assert content_optimizer._apply_seo_retitle(db_session, opportunity) is None

    resp = client.post(f"/api/admin/optimization-actions/{action.id}/revert", headers=admin_headers)
    assert resp.status_code == 200
    db_session.expire_all()
    assert db_session.get(models.Product, weak.id).seo_title_intent is None
    assert db_session.get(models.AiOptimizationAction, action.id).status == "reverted"


def test_a_worse_retitle_is_put_back_automatically_without_a_claude_call(db_session, monkeypatch):
    weak = _product(db_session, "weak")
    weak.seo_title_intent = "timing"
    created = datetime.datetime.utcnow() - datetime.timedelta(days=10)
    action = models.AiOptimizationAction(
        action_type="retitle_product", target_path="/products/weak", product_id=weak.id,
        decision_basis="test", content_before=json.dumps({"seo_title_intent": None}),
        content_after=json.dumps({"seo_title_intent": "timing"}), status="applied", created_at=created,
    )
    db_session.add(action)
    for day, ctr in ((created.date() - datetime.timedelta(days=1), 0.05), (datetime.date.today(), 0.02)):
        db_session.add(models.PageMetricsSnapshot(
            snapshot_date=day, path="/products/weak", product_id=weak.id,
            search_impressions=500, search_clicks=int(500 * ctr), search_ctr=ctr, search_position=5.0,
        ))
    db_session.commit()

    def _no_claude(*args, **kwargs):
        raise AssertionError("a retitle revert must not regenerate copy")

    monkeypatch.setattr(content_optimizer.pipeline, "sync_product_analysis", _no_claude)
    result = content_optimizer.evaluate_past_actions(db_session)

    assert [a.id for a in result.auto_reverted] == [action.id]
    db_session.expire_all()
    assert db_session.get(models.Product, weak.id).seo_title_intent is None


def test_product_api_exposes_the_title_intent(client, db_session):
    p = _product(db_session, "g440")
    p.buy_score = "good"
    p.seo_title_intent = "spec"
    db_session.commit()
    assert client.get("/api/products/g440").json()["seo_title_intent"] == "spec"
