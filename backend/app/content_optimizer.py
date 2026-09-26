"""Rule-based decision engine for the STEP42 autonomous content-optimization
loop. Deciding WHAT to do is deterministic and free (no Claude call) - same
principle as analysis.py's rule_based_reason()/AiTeamDashboard.tsx's
buildPlanningSession(): every decision quotes a real, stored number and a
stated threshold, never a guess. Only the actual content generation step
(app/content_rewriter.py) spends real money, and it's capped at
DAILY_ACTION_CAP actions per run - explicitly approved by the president
(see docs/ai_company_guidelines.md STEP42) after being told this has a
real per-call cost.

Every action taken is logged to AiOptimizationAction with its real
decision basis, and evaluate_past_actions() later fills in whether it
actually helped by comparing real PageMetricsSnapshot/AffiliateClick data
from before vs after - this table is the "ナレッジ" the president asked
this loop to build up over time, not just a one-off log line.
"""

import dataclasses
import datetime
import json
import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import content_metrics, content_rewriter, crud, models, search_console
from app.brands import match_brand

# A rewrite/new-guide costs a real Claude API call - capped low and
# explicitly approved by the president (STEP42) rather than left
# unbounded. Homepage reordering is free (no Claude call) and isn't
# counted against this cap.
DAILY_ACTION_CAP = 3

# A page needs at least this many real snapshots (i.e. at least 2 - one
# earlier, one later) before "declining" is a claim this code will make -
# a single data point has no trend (see PageMetricsSnapshot's docstring).
MIN_SNAPSHOTS_FOR_TREND = 2
UNDERPERFORMING_LOOKBACK_DAYS = 21
DECLINE_THRESHOLD_PCT = 20.0
# Below these, a swing is noise, not a real signal worth acting on.
MIN_BASELINE_PAGEVIEWS = 10
MIN_BASELINE_SEARCH_IMPRESSIONS = 20

# Don't rewrite the same product again while its last rewrite's effect
# hasn't been measured yet (see evaluate_past_actions) - otherwise the
# loop could churn the same page's copy every single day.
REWRITE_COOLDOWN_DAYS = 7

TRENDING_LOOKBACK_DAYS = 7
TRENDING_LIMIT = 6

NEW_GUIDE_MIN_PRODUCTS = 3
NEW_GUIDE_MIN_IMPRESSIONS = 20

EFFECT_EVALUATION_DELAY_DAYS = 7
EFFECT_IMPROVE_THRESHOLD_PCT = 10.0


@dataclasses.dataclass
class UnderperformingFinding:
    product: models.Product
    decision_basis: str


@dataclasses.dataclass
class GuideOpportunity:
    query_text: str
    brand: str
    category: str
    products: list[models.Product]
    impressions: int


@dataclasses.dataclass
class OptimizationRunResult:
    ga4_available: bool
    search_console_available: bool
    actions_evaluated: int
    actions: list[models.AiOptimizationAction]


def _recent_rewrite_exists(db: Session, product_id: int) -> bool:
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=REWRITE_COOLDOWN_DAYS)
    row = db.execute(
        select(models.AiOptimizationAction.id).where(
            models.AiOptimizationAction.action_type == "rewrite_product",
            models.AiOptimizationAction.product_id == product_id,
            models.AiOptimizationAction.created_at >= cutoff,
        )
    ).first()
    return row is not None


def find_underperforming_products(db: Session, lookback_days: int = UNDERPERFORMING_LOOKBACK_DAYS) -> list[UnderperformingFinding]:
    """A product qualifies only when at least 2 real snapshots exist for
    its page and the metric (search CTR, or pageviews when Search Console
    isn't configured) declined by at least DECLINE_THRESHOLD_PCT between
    the earliest and latest snapshot in the window - never from a single
    data point, and never below the noise floors above."""
    since = datetime.date.today() - datetime.timedelta(days=lookback_days)
    rows = list(
        db.execute(
            select(models.PageMetricsSnapshot)
            .where(models.PageMetricsSnapshot.product_id.is_not(None), models.PageMetricsSnapshot.snapshot_date >= since)
            .order_by(models.PageMetricsSnapshot.snapshot_date.asc())
        ).scalars()
    )
    by_product: dict[int, list[models.PageMetricsSnapshot]] = {}
    for row in rows:
        by_product.setdefault(row.product_id, []).append(row)

    findings: list[UnderperformingFinding] = []
    for product_id, snapshots in by_product.items():
        if len(snapshots) < MIN_SNAPSHOTS_FOR_TREND:
            continue
        if _recent_rewrite_exists(db, product_id):
            continue
        baseline, latest = snapshots[0], snapshots[-1]

        basis = None
        if baseline.search_ctr is not None and latest.search_ctr is not None and baseline.search_impressions is not None:
            if baseline.search_impressions >= MIN_BASELINE_SEARCH_IMPRESSIONS and baseline.search_ctr > 0:
                decline = (latest.search_ctr - baseline.search_ctr) / baseline.search_ctr * 100
                if decline <= -DECLINE_THRESHOLD_PCT:
                    basis = (
                        f"検索クリック率が{baseline.snapshot_date}の{baseline.search_ctr * 100:.1f}%から"
                        f"{latest.snapshot_date}の{latest.search_ctr * 100:.1f}%へ{abs(round(decline))}%低下"
                    )
        if basis is None and baseline.pageviews is not None and latest.pageviews is not None:
            if baseline.pageviews >= MIN_BASELINE_PAGEVIEWS:
                decline = (latest.pageviews - baseline.pageviews) / baseline.pageviews * 100
                if decline <= -DECLINE_THRESHOLD_PCT:
                    basis = (
                        f"ページビューが{baseline.snapshot_date}の{baseline.pageviews}件から"
                        f"{latest.snapshot_date}の{latest.pageviews}件へ{abs(round(decline))}%低下"
                    )
        if basis is None:
            continue

        product = db.get(models.Product, product_id)
        if product is None or product.pending_review:
            continue
        findings.append(UnderperformingFinding(product=product, decision_basis=basis))

    return findings


def select_trending_products(
    db: Session, days: int = TRENDING_LOOKBACK_DAYS, limit: int = TRENDING_LIMIT
) -> list[tuple[models.Product, int]]:
    """Real 7-day AffiliateClick leaders - never padded with an arbitrary
    product when there's no real click activity (returns [] in that case)."""
    since = datetime.datetime.utcnow() - datetime.timedelta(days=days)
    rows = db.execute(
        select(models.AffiliateClick.product_id, func.count().label("clicks"))
        .where(models.AffiliateClick.created_at >= since, models.AffiliateClick.product_id.is_not(None))
        .group_by(models.AffiliateClick.product_id)
        .order_by(func.count().desc())
        .limit(limit)
    ).all()
    if not rows:
        return []

    products_by_id = {
        p.id: p
        for p in db.execute(
            select(models.Product).where(
                models.Product.id.in_([r[0] for r in rows]), models.Product.pending_review.is_(False)
            )
        ).scalars()
    }
    return [(products_by_id[pid], count) for pid, count in rows if pid in products_by_id]


def find_new_guide_opportunities(db: Session) -> list[GuideOpportunity]:
    """A brand-specific guide topic, never a bare category (the site's
    existing hand-authored guides already cover "ドライバー比較"/"アイアン
    セット比較" generically - see frontend/lib/guides.ts - so this stays
    naturally non-duplicative by only drafting brand-level topics). Only
    considers a query that (a) has real, non-trivial search impressions,
    (b) matches a real brand in this catalog via app.brands.match_brand,
    (c) has enough real matching products to be worth a dedicated page,
    and (d) hasn't already been drafted before (based_on_query)."""
    try:
        queries = search_console.get_top_queries(days=28, limit=50)
    except search_console.SearchConsoleNotConfigured:
        return []

    already_drafted = {
        row for row in db.execute(select(models.GuideArticle.based_on_query)).scalars() if row
    }
    products = list(
        db.execute(select(models.Product).where(models.Product.pending_review.is_(False))).scalars()
    )

    opportunities: list[GuideOpportunity] = []
    for q in queries:
        if q.impressions < NEW_GUIDE_MIN_IMPRESSIONS or q.query in already_drafted:
            continue
        brand = match_brand(q.query)
        if brand is None:
            continue
        brand_products = [p for p in products if p.brand == brand]
        if len(brand_products) < NEW_GUIDE_MIN_PRODUCTS:
            continue

        by_category: dict[str, list[models.Product]] = {}
        for p in brand_products:
            by_category.setdefault(p.category, []).append(p)
        category, category_products = max(by_category.items(), key=lambda kv: len(kv[1]))
        if len(category_products) < NEW_GUIDE_MIN_PRODUCTS:
            continue

        opportunities.append(
            GuideOpportunity(query_text=q.query, brand=brand, category=category, products=category_products[:6], impressions=q.impressions)
        )

    opportunities.sort(key=lambda o: o.impressions, reverse=True)
    return opportunities


def _slugify_guide(brand: str, category: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", f"{brand}-{category}-guide".lower()).strip("-")
    return base


def _apply_homepage_reorder(db: Session, trending: list[tuple[models.Product, int]]) -> models.AiOptimizationAction:
    basis = "直近7日間のクリック数上位: " + "、".join(f"{p.name}（{count}件）" for p, count in trending)
    action = models.AiOptimizationAction(
        action_type="reorder_homepage",
        target_path="/",
        decision_basis=basis,
        content_after=json.dumps({"product_ids": [p.id for p, _ in trending]}),
        status="applied",
    )
    db.add(action)
    db.commit()
    db.refresh(action)
    return action


def _apply_product_rewrite(db: Session, finding: UnderperformingFinding) -> models.AiOptimizationAction:
    product = finding.product
    content_before = json.dumps(
        {"ai_title": product.ai_title, "ai_summary": product.ai_summary, "ai_caution": product.ai_caution},
        ensure_ascii=False,
    )
    try:
        rewritten = content_rewriter.rewrite_product_copy(product, finding.decision_basis)
    except Exception as exc:  # noqa: BLE001 - log the failure as knowledge, never crash the run
        action = models.AiOptimizationAction(
            action_type="rewrite_product",
            target_path=f"/products/{product.slug}",
            product_id=product.id,
            decision_basis=finding.decision_basis,
            content_before=content_before,
            status="failed",
        )
        db.add(action)
        crud.create_error_log(db, source="content_optimizer", message=f"product rewrite failed for {product.name}: {exc}")
        db.commit()
        db.refresh(action)
        return action

    product.ai_title = rewritten.title
    product.ai_summary = rewritten.summary
    product.ai_caution = rewritten.caution
    product.ai_generated_at = datetime.datetime.utcnow()
    content_after = json.dumps(
        {"ai_title": rewritten.title, "ai_summary": rewritten.summary, "ai_caution": rewritten.caution},
        ensure_ascii=False,
    )
    action = models.AiOptimizationAction(
        action_type="rewrite_product",
        target_path=f"/products/{product.slug}",
        product_id=product.id,
        decision_basis=finding.decision_basis,
        content_before=content_before,
        content_after=content_after,
        status="applied",
    )
    db.add(action)
    db.commit()
    db.refresh(action)
    return action


def _apply_new_guide(db: Session, opportunity: GuideOpportunity) -> models.AiOptimizationAction:
    basis = f"検索クエリ「{opportunity.query_text}」（インプレッション{opportunity.impressions}件）に対応する既存ガイドが無いため新規作成"
    try:
        draft = content_rewriter.draft_new_guide(opportunity.query_text, opportunity.products)
    except Exception as exc:  # noqa: BLE001 - log the failure as knowledge, never crash the run
        action = models.AiOptimizationAction(
            action_type="new_guide", target_path="/guides", decision_basis=basis, status="failed"
        )
        db.add(action)
        crud.create_error_log(db, source="content_optimizer", message=f"new guide draft failed for query '{opportunity.query_text}': {exc}")
        db.commit()
        db.refresh(action)
        return action

    slug_base = _slugify_guide(opportunity.brand, opportunity.category)
    slug = slug_base
    suffix = 2
    while db.execute(select(models.GuideArticle.id).where(models.GuideArticle.slug == slug)).first() is not None:
        slug = f"{slug_base}-{suffix}"
        suffix += 1

    guide = models.GuideArticle(
        slug=slug,
        title=draft.title,
        description=draft.description,
        published_at=datetime.date.today(),
        related_categories=opportunity.category,
        featured_kind="top_buy_signal",
        featured_category=opportunity.category,
        featured_heading=f"{opportunity.brand}の注目商品",
        featured_limit=6,
        sections_json=json.dumps(
            [{"heading": s.heading, "paragraphs": s.paragraphs} for s in draft.sections], ensure_ascii=False
        ),
        source="ai_generated",
        based_on_query=opportunity.query_text,
    )
    db.add(guide)
    action = models.AiOptimizationAction(
        action_type="new_guide",
        target_path=f"/guides/{slug}",
        guide_slug=slug,
        decision_basis=basis,
        content_after=json.dumps({"title": draft.title, "slug": slug}, ensure_ascii=False),
        status="applied",
    )
    db.add(action)
    db.commit()
    db.refresh(action)
    return action


def _pct_change(before: float, after: float) -> float | None:
    if before == 0:
        return None
    return (after - before) / before * 100


def _evaluate_content_action(db: Session, action: models.AiOptimizationAction) -> tuple[str, str] | None:
    baseline = db.execute(
        select(models.PageMetricsSnapshot)
        .where(
            models.PageMetricsSnapshot.path == action.target_path,
            models.PageMetricsSnapshot.snapshot_date <= action.created_at.date(),
        )
        .order_by(models.PageMetricsSnapshot.snapshot_date.desc())
    ).scalars().first()
    latest = db.execute(
        select(models.PageMetricsSnapshot)
        .where(
            models.PageMetricsSnapshot.path == action.target_path,
            models.PageMetricsSnapshot.snapshot_date > action.created_at.date(),
        )
        .order_by(models.PageMetricsSnapshot.snapshot_date.desc())
    ).scalars().first()
    if baseline is None or latest is None:
        return None

    if baseline.search_ctr is not None and latest.search_ctr is not None and baseline.search_ctr > 0:
        change = _pct_change(baseline.search_ctr, latest.search_ctr)
        metric_label = "検索クリック率"
        before_str, after_str = f"{baseline.search_ctr * 100:.1f}%", f"{latest.search_ctr * 100:.1f}%"
    elif baseline.pageviews is not None and latest.pageviews is not None and baseline.pageviews > 0:
        change = _pct_change(baseline.pageviews, latest.pageviews)
        metric_label = "ページビュー"
        before_str, after_str = f"{baseline.pageviews}件", f"{latest.pageviews}件"
    else:
        return None

    if change is None:
        return None
    verdict = "improved" if change >= EFFECT_IMPROVE_THRESHOLD_PCT else "worse" if change <= -EFFECT_IMPROVE_THRESHOLD_PCT else "no_change"
    summary = f"{metric_label}が{before_str}→{after_str}（{'+' if change >= 0 else ''}{round(change)}%）"
    return summary, verdict


def _evaluate_homepage_action(db: Session, action: models.AiOptimizationAction) -> tuple[str, str] | None:
    if not action.content_after:
        return None
    product_ids = json.loads(action.content_after).get("product_ids", [])
    if not product_ids:
        return None

    before_start = action.created_at - datetime.timedelta(days=TRENDING_LOOKBACK_DAYS)
    after_end = action.created_at + datetime.timedelta(days=TRENDING_LOOKBACK_DAYS)
    if datetime.datetime.utcnow() < after_end:
        return None  # not enough time has passed to measure the "after" window yet

    def _click_count(start: datetime.datetime, end: datetime.datetime) -> int:
        return db.execute(
            select(func.count()).where(
                models.AffiliateClick.product_id.in_(product_ids),
                models.AffiliateClick.created_at >= start,
                models.AffiliateClick.created_at < end,
            )
        ).scalar_one()

    before = _click_count(before_start, action.created_at)
    after = _click_count(action.created_at, after_end)
    change = _pct_change(before, after)
    if change is None:
        return (f"クリック数 {before}件→{after}件", "no_change" if after == 0 else "improved")
    verdict = "improved" if change >= EFFECT_IMPROVE_THRESHOLD_PCT else "worse" if change <= -EFFECT_IMPROVE_THRESHOLD_PCT else "no_change"
    return f"クリック数が{before}件→{after}件（{'+' if change >= 0 else ''}{round(change)}%）", verdict


def evaluate_past_actions(db: Session, delay_days: int = EFFECT_EVALUATION_DELAY_DAYS) -> int:
    """Fills in effect_summary/effect_verdict on any applied action old
    enough to judge, using real snapshot/click data from before vs after -
    never a guess. An action without enough data yet is simply skipped and
    retried on a later run."""
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=delay_days)
    pending = db.execute(
        select(models.AiOptimizationAction).where(
            models.AiOptimizationAction.effect_evaluated_at.is_(None),
            models.AiOptimizationAction.status == "applied",
            models.AiOptimizationAction.created_at <= cutoff,
        )
    ).scalars().all()

    evaluated = 0
    for action in pending:
        result = (
            _evaluate_homepage_action(db, action)
            if action.action_type == "reorder_homepage"
            else _evaluate_content_action(db, action)
        )
        if result is None:
            continue
        summary, verdict = result
        action.effect_evaluated_at = datetime.datetime.utcnow()
        action.effect_summary = summary
        action.effect_verdict = verdict
        evaluated += 1

    if evaluated:
        db.commit()
    return evaluated


def run_daily_optimization(db: Session) -> OptimizationRunResult:
    snapshot = content_metrics.capture_daily_snapshot(db)
    evaluated = evaluate_past_actions(db)

    actions: list[models.AiOptimizationAction] = []

    trending = select_trending_products(db)
    if trending:
        actions.append(_apply_homepage_reorder(db, trending))

    remaining = DAILY_ACTION_CAP
    if remaining > 0:
        for finding in find_underperforming_products(db):
            if remaining <= 0:
                break
            actions.append(_apply_product_rewrite(db, finding))
            remaining -= 1

    if remaining > 0:
        for opportunity in find_new_guide_opportunities(db):
            if remaining <= 0:
                break
            actions.append(_apply_new_guide(db, opportunity))
            remaining -= 1

    return OptimizationRunResult(
        ga4_available=snapshot.ga4_available,
        search_console_available=snapshot.search_console_available,
        actions_evaluated=evaluated,
        actions=actions,
    )
