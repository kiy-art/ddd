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

from app import ai, content_metrics, content_rewriter, crud, models, pipeline, search_console
from app.brands import match_brand
from app.config import get_settings

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


# STEP43: "成果に直結する改善" prioritization. Every candidate improvement
# is expressed in the one unit closest to revenue this site can actually
# measure - estimated extra affiliate (shop) clicks - and then weighted by
# price, because affiliate commission is a percentage of the sale: the
# same click gap on a ¥80,000 driver is worth ~16x one on a ¥5,000 dozen
# of balls. That makes priority_score a *relative* ranking under a stated
# assumption (similar purchase and commission rates across products), not
# a yen forecast - no real commission data is integrated (see
# daily_report.py's note on 収益). The daily Claude budget
# (DAILY_ACTION_CAP) then goes to the highest-scoring pages first, and
# existing pages with proven traffic are improved before any new guide is
# drafted (the standard affiliate-SEO order: fix what already ranks
# before writing more).
GOAL_SEARCH_CTR = "search_ctr"
GOAL_ON_PAGE_CONVERSION = "on_page_conversion"

# Cross-sectional (single snapshot) gaps vs. this site's own product-page
# average - a comparison across pages on the same day, not a claimed
# trend, so one snapshot is enough.
SEARCH_GAP_MIN_IMPRESSIONS = 50
# Past ~page 2 of results, a better title rarely unlocks clicks - the
# ranking itself is the bottleneck, which copy can't fix.
SEARCH_GAP_MAX_POSITION = 20.0
CONVERSION_GAP_MIN_PAGEVIEWS = 30
CONVERSION_LOOKBACK_DAYS = 7
# Must be at least this far below the site average to count - a small
# gap is within normal page-to-page variation.
GAP_MIN_RATIO = 0.3


@dataclasses.dataclass
class ImprovementOpportunity:
    product: models.Product
    goal: str
    decision_basis: str
    est_extra_shop_clicks: float  # in shop clicks, or search visits when shop_click_rate_known is False
    priority_score: float
    shop_click_rate_known: bool


@dataclasses.dataclass
class GuideOpportunity:
    query_text: str
    brand: str
    category: str
    products: list[models.Product]
    impressions: int


# STEP44: a rewrite_product action whose measured effect is "worse" is
# undone automatically - but only when the before/after numbers rest on a
# real sample, so one quiet day can't trigger it. Same minimums the
# detectors already require before calling a page's numbers meaningful.
AUTO_REVERT_MIN_SEARCH_IMPRESSIONS = MIN_BASELINE_SEARCH_IMPRESSIONS
AUTO_REVERT_MIN_PAGEVIEWS = MIN_BASELINE_PAGEVIEWS


@dataclasses.dataclass
class EvaluationRunResult:
    evaluated: int
    auto_reverted: list[models.AiOptimizationAction] = dataclasses.field(default_factory=list)


@dataclasses.dataclass
class OptimizationRunResult:
    ga4_available: bool
    search_console_available: bool
    actions_evaluated: int
    actions: list[models.AiOptimizationAction]
    actions_auto_reverted: list[models.AiOptimizationAction] = dataclasses.field(default_factory=list)


def _recent_rewrite_exists(db: Session, product_id: int) -> bool:
    """A product rewritten - or reverted (STEP44) - within the cooldown is
    left alone: a revert puts routine copy back, and the next rewrite needs
    fresh post-revert numbers to be judged against, not the same run's."""
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=REWRITE_COOLDOWN_DAYS)
    row = db.execute(
        select(models.AiOptimizationAction.id).where(
            models.AiOptimizationAction.action_type == "rewrite_product",
            models.AiOptimizationAction.product_id == product_id,
            (models.AiOptimizationAction.created_at >= cutoff) | (models.AiOptimizationAction.reverted_at >= cutoff),
        )
    ).first()
    return row is not None


def _site_search_ctr(latest: dict[int, models.PageMetricsSnapshot]) -> float | None:
    rows = [r for r in latest.values() if r.search_impressions and r.search_clicks is not None]
    impressions = sum(r.search_impressions for r in rows)
    return sum(r.search_clicks for r in rows) / impressions if impressions > 0 else None


def _product_pageviews_since(db: Session, since: datetime.date) -> dict[int, int]:
    rows = db.execute(
        select(models.PageMetricsSnapshot.product_id, func.sum(models.PageMetricsSnapshot.pageviews))
        .where(
            models.PageMetricsSnapshot.product_id.is_not(None),
            models.PageMetricsSnapshot.pageviews.is_not(None),
            models.PageMetricsSnapshot.snapshot_date >= since,
        )
        .group_by(models.PageMetricsSnapshot.product_id)
    ).all()
    return {pid: int(pv or 0) for pid, pv in rows}


def _product_clicks_since(db: Session, since: datetime.datetime) -> dict[int, int]:
    rows = db.execute(
        select(models.AffiliateClick.product_id, func.count())
        .where(models.AffiliateClick.product_id.is_not(None), models.AffiliateClick.created_at >= since)
        .group_by(models.AffiliateClick.product_id)
    ).all()
    return {pid: count for pid, count in rows}


def _site_shop_click_rate(pageviews: dict[int, int], clicks: dict[int, int]) -> float | None:
    # Same denominator population on both sides: only products with real
    # pageview data, so the rate isn't inflated by clicks on untracked pages.
    total_pv = sum(pageviews.values())
    if total_pv == 0:
        return None
    rate = sum(clicks.get(pid, 0) for pid in pageviews) / total_pv
    return rate or None


def _trend_decline(snapshots: list[models.PageMetricsSnapshot]) -> tuple[str, float] | None:
    """(basis, lost search visits) when a real decline exists between the
    earliest and latest snapshot - never from a single data point."""
    if len(snapshots) < MIN_SNAPSHOTS_FOR_TREND:
        return None
    baseline, latest = snapshots[0], snapshots[-1]

    if (
        baseline.search_ctr is not None
        and latest.search_ctr is not None
        and baseline.search_impressions is not None
        and baseline.search_impressions >= MIN_BASELINE_SEARCH_IMPRESSIONS
        and baseline.search_ctr > 0
    ):
        decline = (latest.search_ctr - baseline.search_ctr) / baseline.search_ctr * 100
        if decline <= -DECLINE_THRESHOLD_PCT:
            lost = (latest.search_impressions or baseline.search_impressions) * (baseline.search_ctr - latest.search_ctr)
            return (
                f"検索クリック率が{baseline.snapshot_date}の{baseline.search_ctr * 100:.1f}%から"
                f"{latest.snapshot_date}の{latest.search_ctr * 100:.1f}%へ{abs(round(decline))}%低下",
                lost,
            )

    if baseline.pageviews is not None and latest.pageviews is not None and baseline.pageviews >= MIN_BASELINE_PAGEVIEWS:
        decline = (latest.pageviews - baseline.pageviews) / baseline.pageviews * 100
        if decline <= -DECLINE_THRESHOLD_PCT:
            return (
                f"ページビューが{baseline.snapshot_date}の{baseline.pageviews}件から"
                f"{latest.snapshot_date}の{latest.pageviews}件へ{abs(round(decline))}%低下",
                float(baseline.pageviews - latest.pageviews),
            )
    return None


def _search_ctr_gap(snapshot: models.PageMetricsSnapshot, site_ctr: float | None) -> tuple[str, float] | None:
    if site_ctr is None or snapshot.search_ctr is None or snapshot.search_position is None:
        return None
    if (snapshot.search_impressions or 0) < SEARCH_GAP_MIN_IMPRESSIONS:
        return None
    if snapshot.search_position > SEARCH_GAP_MAX_POSITION:
        return None
    if snapshot.search_ctr >= site_ctr * (1 - GAP_MIN_RATIO):
        return None
    extra = snapshot.search_impressions * (site_ctr - snapshot.search_ctr)
    return (
        f"検索表示{snapshot.search_impressions:,}回・平均掲載順位{snapshot.search_position}位に対し"
        f"検索クリック率{snapshot.search_ctr:.1%}（商品ページ平均{site_ctr:.1%}）。平均並みになれば直近"
        f"{content_metrics.SEARCH_CONSOLE_WINDOW_DAYS}日で約{extra:.0f}件の検索流入増が見込めるため、"
        "検索結果での訴求（タイトル）を改善",
        extra,
    )


def _conversion_gap(pageviews: int, clicks: int, shop_rate: float | None) -> tuple[str, float] | None:
    if shop_rate is None or pageviews < CONVERSION_GAP_MIN_PAGEVIEWS:
        return None
    rate = clicks / pageviews
    if rate >= shop_rate * (1 - GAP_MIN_RATIO):
        return None
    extra = pageviews * (shop_rate - rate)
    return (
        f"直近{CONVERSION_LOOKBACK_DAYS}日間で{pageviews}PVに対しショップへのクリック{clicks}件"
        f"（{rate:.1%}、商品ページ平均{shop_rate:.1%}）。平均並みになれば約{extra:.1f}件のクリック増が"
        "見込めるため、ページ上の購入判断の訴求（説明文）を改善",
        extra,
    )


def find_improvement_opportunities(db: Session) -> list[ImprovementOpportunity]:
    """Every product page with a real, measurable gap, ranked by expected
    revenue impact (see the STEP43 note above). Three detectors, all from
    stored real data: search CTR well below the site's product-page
    average (title problem), shop-click rate well below average (on-page
    persuasion problem), and a real decline between two snapshots. A
    product under its post-rewrite measurement window is skipped."""
    today = datetime.date.today()
    snapshots = list(
        db.execute(
            select(models.PageMetricsSnapshot)
            .where(
                models.PageMetricsSnapshot.product_id.is_not(None),
                models.PageMetricsSnapshot.snapshot_date >= today - datetime.timedelta(days=UNDERPERFORMING_LOOKBACK_DAYS),
            )
            .order_by(models.PageMetricsSnapshot.snapshot_date.asc())
        ).scalars()
    )
    by_product: dict[int, list[models.PageMetricsSnapshot]] = {}
    for row in snapshots:
        by_product.setdefault(row.product_id, []).append(row)
    latest = {pid: rows[-1] for pid, rows in by_product.items()}

    site_ctr = _site_search_ctr(latest)
    pageviews = _product_pageviews_since(db, today - datetime.timedelta(days=CONVERSION_LOOKBACK_DAYS))
    clicks = _product_clicks_since(db, datetime.datetime.utcnow() - datetime.timedelta(days=CONVERSION_LOOKBACK_DAYS))
    shop_rate = _site_shop_click_rate(pageviews, clicks)

    # (goal, basis, value in shop clicks - or search visits when shop_rate is unknown)
    candidates: dict[int, list[tuple[str, str, float]]] = {}

    def _as_shop_clicks(visits: float) -> float:
        return visits * shop_rate if shop_rate else visits

    for pid, rows in by_product.items():
        trend = _trend_decline(rows)
        if trend:
            candidates.setdefault(pid, []).append((GOAL_SEARCH_CTR, trend[0], _as_shop_clicks(trend[1])))
        gap = _search_ctr_gap(latest[pid], site_ctr)
        if gap:
            candidates.setdefault(pid, []).append((GOAL_SEARCH_CTR, gap[0], _as_shop_clicks(gap[1])))
    for pid, pv in pageviews.items():
        gap = _conversion_gap(pv, clicks.get(pid, 0), shop_rate)
        if gap:
            candidates.setdefault(pid, []).append((GOAL_ON_PAGE_CONVERSION, gap[0], gap[1]))

    opportunities: list[ImprovementOpportunity] = []
    for pid, options in candidates.items():
        product = db.get(models.Product, pid)
        if product is None or product.pending_review or _recent_rewrite_exists(db, pid):
            continue
        goal, basis, value = max(options, key=lambda o: o[2])
        price = product.current_price or 0
        score = value * max(price, 1)
        unit = "推定ショップクリック増" if shop_rate else "推定検索流入増（ショップクリック率が未蓄積のため流入数で換算）"
        basis += f"【優先度】{unit}{value:.1f}件×価格¥{price:,}＝{score:,.0f}（想定報酬の相対値）"
        opportunities.append(
            ImprovementOpportunity(
                product=product,
                goal=goal,
                decision_basis=basis,
                est_extra_shop_clicks=round(value, 2),
                priority_score=round(score, 1),
                shop_click_rate_known=bool(shop_rate),
            )
        )

    opportunities.sort(key=lambda o: o.priority_score, reverse=True)
    return opportunities


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


def _real_queries_for(db: Session, product: models.Product) -> list[dict]:
    url = f"{get_settings().site_url.rstrip('/')}/products/{product.slug}"
    try:
        rows = search_console.get_queries_for_page(url, days=28, limit=5)
    except search_console.SearchConsoleNotConfigured:
        return []
    except Exception as exc:  # noqa: BLE001 - a missing query list shouldn't block the rewrite itself
        crud.create_error_log(db, source="content_optimizer", level="warning", message=f"search query lookup failed for {url}: {exc}")
        return []
    return [dataclasses.asdict(r) for r in rows]


def _apply_product_rewrite(db: Session, opportunity: ImprovementOpportunity) -> models.AiOptimizationAction:
    product = opportunity.product
    content_before = json.dumps(
        {"ai_title": product.ai_title, "ai_summary": product.ai_summary, "ai_caution": product.ai_caution},
        ensure_ascii=False,
    )
    queries = _real_queries_for(db, product) if opportunity.goal == GOAL_SEARCH_CTR else []
    try:
        rewritten = content_rewriter.rewrite_product_copy(
            product, opportunity.decision_basis, goal=opportunity.goal, search_queries=queries
        )
    except Exception as exc:  # noqa: BLE001 - log the failure as knowledge, never crash the run
        action = models.AiOptimizationAction(
            action_type="rewrite_product",
            target_path=f"/products/{product.slug}",
            product_id=product.id,
            decision_basis=opportunity.decision_basis,
            content_before=content_before,
            status="failed",
        )
        db.add(action)
        crud.create_error_log(db, source="content_optimizer", message=f"product rewrite failed for {product.name}: {exc}")
        db.commit()
        db.refresh(action)
        return action

    action = models.AiOptimizationAction(
        action_type="rewrite_product",
        target_path=f"/products/{product.slug}",
        product_id=product.id,
        decision_basis=opportunity.decision_basis,
        content_before=content_before,
        content_after=json.dumps(
            {
                "ai_title": rewritten.title,
                "ai_summary": rewritten.summary,
                "ai_caution": rewritten.caution,
                "goal": opportunity.goal,
                "queries": queries,
            },
            ensure_ascii=False,
        ),
        status="applied",
    )
    db.add(action)
    db.flush()

    product.ai_title = rewritten.title
    product.ai_summary = rewritten.summary
    product.ai_caution = rewritten.caution
    product.ai_generated_at = datetime.datetime.utcnow()
    product.ai_copy_source_action_id = action.id
    # Marks this copy as current for today's facts, so the routine analysis
    # stage doesn't immediately regenerate it; when facts do change,
    # pipeline.sync_product_analysis regenerates in this action's style.
    product.ai_content_hash = ai.content_hash(product.name, product.current_price, product.buy_score, product.average_price)
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


def _evaluate_content_action(db: Session, action: models.AiOptimizationAction) -> tuple[str, str, bool] | None:
    """(summary, verdict, sample_sufficient). sample_sufficient says whether
    both the before and after numbers rest on enough real traffic to act on
    automatically (STEP44 auto-revert) - the verdict itself is recorded
    either way, as knowledge."""
    if action.action_type == "rewrite_product":
        product = db.get(models.Product, action.product_id) if action.product_id else None
        if product is None or product.ai_copy_source_action_id != action.id:
            return (
                "評価期間中に文面が別の生成処理（価格変動に伴う通常の再生成など）で置き換わったため、"
                "この施策単独の効果は判定できません",
                "inconclusive",
                False,
            )

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
        sample_sufficient = (
            (baseline.search_impressions or 0) >= AUTO_REVERT_MIN_SEARCH_IMPRESSIONS
            and (latest.search_impressions or 0) >= AUTO_REVERT_MIN_SEARCH_IMPRESSIONS
        )
    elif baseline.pageviews is not None and latest.pageviews is not None and baseline.pageviews > 0:
        change = _pct_change(baseline.pageviews, latest.pageviews)
        metric_label = "ページビュー"
        before_str, after_str = f"{baseline.pageviews}件", f"{latest.pageviews}件"
        sample_sufficient = baseline.pageviews >= AUTO_REVERT_MIN_PAGEVIEWS
    else:
        return None

    if change is None:
        return None
    verdict = "improved" if change >= EFFECT_IMPROVE_THRESHOLD_PCT else "worse" if change <= -EFFECT_IMPROVE_THRESHOLD_PCT else "no_change"
    summary = f"{metric_label}が{before_str}→{after_str}（{'+' if change >= 0 else ''}{round(change)}%）"
    return summary, verdict, sample_sufficient


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


def _auto_revert_worse_rewrite(db: Session, action: models.AiOptimizationAction) -> bool:
    """STEP44: undo a rewrite whose real measured effect was "worse".

    crud.revert_optimization_action restores content_before and clears the
    product's content hash; sync_product_analysis then immediately
    regenerates routine copy from today's real price data, so the restored
    (possibly days-old) text never sits on the page quoting a stale price.
    That regeneration can cost one Claude call, which run_daily_optimization
    deducts from the same DAILY_ACTION_CAP budget - total calls per day stay
    within what the president approved.

    If the revert itself fails, it's logged and the action stays "applied"
    (verdict "worse") for the president to handle from /admin. If only the
    regeneration fails, the revert still stands and the cleared hash makes
    the next daily sync retry it. Neither ever blocks the rest of the run."""
    try:
        crud.revert_optimization_action(db, action.id, reason="auto_worse")
    except Exception as exc:  # noqa: BLE001 - one failed revert must not stop the daily run
        db.rollback()
        crud.create_error_log(
            db, source="content_optimizer", product_id=action.product_id,
            message=f"Auto-revert of optimization action {action.id} failed: {exc}",
        )
        return False

    regenerated_note = "最新の価格データで通常の文面に再生成しました"
    product = db.get(models.Product, action.product_id)
    try:
        if product is not None:
            pipeline.sync_product_analysis(db, product)
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        regenerated_note = "文面の再生成は次回の日次更新で再試行します"
        crud.create_error_log(
            db, source="content_optimizer", product_id=action.product_id,
            message=f"Regeneration after auto-revert of action {action.id} failed: {exc}",
        )

    db.refresh(action)
    action.effect_summary = f"{action.effect_summary} → 悪化と判定したため自動で元に戻し、{regenerated_note}"
    db.commit()
    crud.create_error_log(
        db, source="content_optimizer", level="warning", product_id=action.product_id,
        message=f"自動差し戻し: {action.target_path} の文面変更を元に戻しました（{action.effect_summary}）",
    )
    return True


def evaluate_past_actions(db: Session, delay_days: int = EFFECT_EVALUATION_DELAY_DAYS) -> EvaluationRunResult:
    """Fills in effect_summary/effect_verdict on any applied action old
    enough to judge, using real snapshot/click data from before vs after -
    never a guess. An action without enough data yet is simply skipped and
    retried on a later run.

    STEP44: a rewrite_product judged "worse" on a sufficient real sample
    (AUTO_REVERT_MIN_*) is undone automatically. A "worse" verdict on a thin
    sample is still recorded, but left for the president to judge."""
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=delay_days)
    pending = db.execute(
        select(models.AiOptimizationAction).where(
            models.AiOptimizationAction.effect_evaluated_at.is_(None),
            models.AiOptimizationAction.status == "applied",
            models.AiOptimizationAction.created_at <= cutoff,
        )
    ).scalars().all()

    evaluated = 0
    to_revert: list[models.AiOptimizationAction] = []
    for action in pending:
        if action.action_type == "reorder_homepage":
            homepage_result = _evaluate_homepage_action(db, action)
            result = None if homepage_result is None else (*homepage_result, False)
        else:
            result = _evaluate_content_action(db, action)
        if result is None:
            continue
        summary, verdict, sample_sufficient = result
        action.effect_evaluated_at = datetime.datetime.utcnow()
        action.effect_verdict = verdict
        if verdict == "worse" and action.action_type == "rewrite_product" and not sample_sufficient:
            summary += "（サンプル数が少ないため自動では元に戻していません）"
        action.effect_summary = summary
        evaluated += 1
        if verdict == "worse" and action.action_type == "rewrite_product" and sample_sufficient:
            to_revert.append(action)

    if evaluated:
        db.commit()

    auto_reverted = [action for action in to_revert if _auto_revert_worse_rewrite(db, action)]
    return EvaluationRunResult(evaluated=evaluated, auto_reverted=auto_reverted)


def run_daily_optimization(db: Session) -> OptimizationRunResult:
    snapshot = content_metrics.capture_daily_snapshot(db)
    evaluation = evaluate_past_actions(db)

    actions: list[models.AiOptimizationAction] = []

    trending = select_trending_products(db)
    if trending:
        actions.append(_apply_homepage_reorder(db, trending))

    # Each auto-revert's routine regeneration may have spent a Claude call -
    # it comes out of the same approved daily budget.
    remaining = DAILY_ACTION_CAP - len(evaluation.auto_reverted)
    for opportunity in find_improvement_opportunities(db):
        if remaining <= 0:
            break
        actions.append(_apply_product_rewrite(db, opportunity))
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
        actions_evaluated=evaluation.evaluated,
        actions=actions,
        actions_auto_reverted=evaluation.auto_reverted,
    )
