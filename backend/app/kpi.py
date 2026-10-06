"""STEP71: the company's KPI snapshot in one call (GET /admin/kpi-summary).

Data-driven management (docs/ai_company_operating_model.md 1.2) needs the
same numbers, measured the same way, every time: the weekly management
meeting reads this and appends a row to docs/knowledge/kpi_ledger.csv
(backend/scripts/kpi_snapshot.py), so trends are comparable week to week.

Every figure is a COUNT/SUM over rows this site itself stored - nothing is
estimated. Where a source covers only part of the site (GA4 / Search
Console snapshots keep the top SNAPSHOT_PAGE_LIMIT pages per day), the
response says so. No personal data: price alerts are counted, never
listed (no email addresses).
"""

import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import content_metrics, crud, email, models


def _count(db: Session, query) -> int:
    return db.execute(query).scalar_one() or 0


def _shop_filter(partner: bool):
    """STEP75 (#004): shop clicks and partner-offer clicks are separate KPIs."""
    in_partner = models.AffiliateClick.shop.in_(models.PARTNER_OFFER_SHOPS)
    return in_partner if partner else ~in_partner


def _clicks(
    db: Session, since: datetime.datetime | None, until: datetime.datetime | None = None, partner: bool = False
) -> int:
    q = select(func.count(models.AffiliateClick.id)).where(_shop_filter(partner))
    if since is not None:
        q = q.where(models.AffiliateClick.created_at >= since)
    if until is not None:
        q = q.where(models.AffiliateClick.created_at < until)
    return _count(db, q)


def _grouped_clicks(db: Session, column, since: datetime.datetime, partner: bool = False) -> dict[str, int]:
    rows = db.execute(
        select(column, func.count(models.AffiliateClick.id))
        .where(models.AffiliateClick.created_at >= since, _shop_filter(partner))
        .group_by(column)
        .order_by(func.count(models.AffiliateClick.id).desc())
    ).all()
    return {(key or "unknown"): count for key, count in rows}


def _latest_snapshot(db: Session, metric_column) -> dict | None:
    """Site totals from the newest snapshot day that has this metric."""
    latest = db.execute(
        select(func.max(models.PageMetricsSnapshot.snapshot_date)).where(metric_column.is_not(None))
    ).scalar_one()
    if latest is None:
        return None
    rows = db.execute(
        select(models.PageMetricsSnapshot).where(
            models.PageMetricsSnapshot.snapshot_date == latest, metric_column.is_not(None)
        )
    ).scalars().all()
    return {"date": latest.isoformat(), "rows": rows}


MARKET_RECENT_DAYS = 7
MARKET_REFERENCE_DAYS = (23, 37)  # "about 30 days ago": the newest price in this window
MARKET_FLAT_PCT = 1.0  # within ±1% counts as unchanged


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    v = sorted(values)
    mid = len(v) // 2
    return v[mid] if len(v) % 2 else (v[mid - 1] + v[mid]) / 2


def market_price_trend(db: Session, now: datetime.datetime) -> dict:
    """Market condition from our own daily price checks (STEP72).

    Per category: how many published products got cheaper / dearer / stayed
    flat versus about 30 days ago, and the median change. Only products with
    a price both in the last week and in the reference window are compared,
    and the response says how many that is - nothing is filled in.
    """
    recent_since = now - datetime.timedelta(days=MARKET_RECENT_DAYS)
    ref_from = now - datetime.timedelta(days=MARKET_REFERENCE_DAYS[1])
    ref_to = now - datetime.timedelta(days=MARKET_REFERENCE_DAYS[0])
    rows = db.execute(
        crud._published(
            select(models.Product.id, models.Product.category, models.PriceHistory.price, models.PriceHistory.recorded_at)
            .join(models.PriceHistory, models.PriceHistory.product_id == models.Product.id)
        )
        .where(
            models.PriceHistory.recorded_at >= ref_from,
            models.PriceHistory.price > 0,
        )
        .order_by(models.PriceHistory.recorded_at)
    ).all()
    recent: dict[int, int] = {}
    reference: dict[int, int] = {}
    category_of: dict[int, str] = {}
    for product_id, category, price, at in rows:  # ascending, so the last write is the newest
        category_of[product_id] = category
        if at >= recent_since:
            recent[product_id] = price
        elif at < ref_to:
            reference[product_id] = price
    by_category: dict[str, dict] = {}
    changes: dict[str, list[float]] = {}
    for product_id in recent.keys() & reference.keys():
        cat = category_of[product_id]
        pct = (recent[product_id] - reference[product_id]) / reference[product_id] * 100
        bucket = by_category.setdefault(cat, {"compared": 0, "down": 0, "up": 0, "flat": 0})
        bucket["compared"] += 1
        bucket["down" if pct < -MARKET_FLAT_PCT else "up" if pct > MARKET_FLAT_PCT else "flat"] += 1
        changes.setdefault(cat, []).append(pct)
    for cat, bucket in by_category.items():
        median = _median(changes[cat])
        bucket["median_change_pct"] = round(median, 1) if median is not None else None
    return {
        "basis": f"newest price in the last {MARKET_RECENT_DAYS} days vs the newest price "
        f"{MARKET_REFERENCE_DAYS[0]}-{MARKET_REFERENCE_DAYS[1]} days ago (published products only)",
        "by_category": dict(sorted(by_category.items())),
        "new_products_30d": dict(
            db.execute(
                crud._published(select(models.Product.category, func.count(models.Product.id)))
                .where(models.Product.created_at >= now - datetime.timedelta(days=30))
                .group_by(models.Product.category)
            ).all()
        ),
    }


def kpi_summary(db: Session, now: datetime.datetime | None = None) -> dict:
    now = now or datetime.datetime.utcnow()
    d7 = now - datetime.timedelta(days=7)
    d14 = now - datetime.timedelta(days=14)
    d30 = now - datetime.timedelta(days=30)

    published = crud.count_published_products(db)
    by_category = dict(
        db.execute(
            crud._published(select(models.Product.category, func.count(models.Product.id))).group_by(models.Product.category)
        ).all()
    )

    search = _latest_snapshot(db, models.PageMetricsSnapshot.search_impressions)
    search_out = None
    if search:
        impressions = sum(r.search_impressions or 0 for r in search["rows"])
        clicks = sum(r.search_clicks or 0 for r in search["rows"])
        weighted = sum((r.search_position or 0) * (r.search_impressions or 0) for r in search["rows"])
        search_out = {
            "snapshot_date": search["date"],
            "window_days": content_metrics.SEARCH_CONSOLE_WINDOW_DAYS,
            "pages_counted": len(search["rows"]),
            "impressions": impressions,
            "clicks": clicks,
            "ctr": round(clicks / impressions, 4) if impressions else None,
            "avg_position": round(weighted / impressions, 1) if impressions else None,
        }

    ga4 = _latest_snapshot(db, models.PageMetricsSnapshot.pageviews)
    ga4_out = None
    if ga4:
        ga4_out = {
            "snapshot_date": ga4["date"],
            "window_days": content_metrics.GA4_WINDOW_DAYS,
            "pages_counted": len(ga4["rows"]),
            "pageviews": sum(r.pageviews or 0 for r in ga4["rows"]),
        }

    error_rows = db.execute(
        select(models.ErrorLog.level, func.count(models.ErrorLog.id))
        .where(models.ErrorLog.created_at >= d7)
        .group_by(models.ErrorLog.level)
    ).all()
    last_job = db.execute(
        select(models.ErrorLog.created_at, models.ErrorLog.message)
        .where(models.ErrorLog.source == "daily_job")
        .order_by(models.ErrorLog.created_at.desc())
        .limit(1)
    ).first()
    actions = db.execute(
        select(models.AiOptimizationAction.action_type, models.AiOptimizationAction.effect_verdict, func.count())
        .where(models.AiOptimizationAction.created_at >= d30)
        .group_by(models.AiOptimizationAction.action_type, models.AiOptimizationAction.effect_verdict)
    ).all()

    return {
        "generated_at": now.replace(microsecond=0).isoformat() + "Z",
        "catalog": {
            "published_products": published,
            "products_total": _count(db, select(func.count(models.Product.id))),
            "pending_review": _count(
                db, select(func.count(models.Product.id)).where(models.Product.pending_review.is_(True))
            ),
            "published_by_category": by_category,
            "with_image": _count(
                db,
                crud._published(select(func.count(models.Product.id))).where(models.Product.image_url.is_not(None)),
            ),
        },
        "shop_clicks": {
            "total": _clicks(db, None),
            "last_7d": _clicks(db, d7),
            "prev_7d": _clicks(db, d14, d7),
            "last_30d": _clicks(db, d30),
            "last_7d_by_shop": _grouped_clicks(db, models.AffiliateClick.shop, d7),
            "last_7d_by_placement": _grouped_clicks(db, models.AffiliateClick.placement, d7),
        },
        # STEP75 (#004): fitting/lesson offer clicks - never in the shop rate.
        "partner_clicks": {
            "total": _clicks(db, None, partner=True),
            "last_7d": _clicks(db, d7, partner=True),
            "last_30d": _clicks(db, d30, partner=True),
            "last_7d_by_placement": _grouped_clicks(db, models.AffiliateClick.placement, d7, partner=True),
        },
        "search_console": search_out,
        "ga4": ga4_out,
        "snapshot_page_limit": content_metrics.SNAPSHOT_PAGE_LIMIT,
        "price_alerts": {
            "total": _count(db, select(func.count(models.PriceAlert.id))),
            "notified": _count(
                db, select(func.count(models.PriceAlert.id)).where(models.PriceAlert.notified_at.is_not(None))
            ),
            "visitor_email_enabled": email.can_email_visitors(),
        },
        "errors_last_7d": {level: count for level, count in error_rows},
        "last_daily_job": (
            {"at": last_job[0].replace(microsecond=0).isoformat() + "Z", "summary": last_job[1]} if last_job else None
        ),
        "market": market_price_trend(db, now),
        "optimization_actions_last_30d": [
            {"type": t, "verdict": v or "not_evaluated", "count": c} for t, v, c in actions
        ],
    }
