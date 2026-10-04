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


def _clicks(db: Session, since: datetime.datetime, until: datetime.datetime | None = None) -> int:
    q = select(func.count(models.AffiliateClick.id)).where(models.AffiliateClick.created_at >= since)
    if until is not None:
        q = q.where(models.AffiliateClick.created_at < until)
    return _count(db, q)


def _grouped_clicks(db: Session, column, since: datetime.datetime) -> dict[str, int]:
    rows = db.execute(
        select(column, func.count(models.AffiliateClick.id))
        .where(models.AffiliateClick.created_at >= since)
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
            "total": _count(db, select(func.count(models.AffiliateClick.id))),
            "last_7d": _clicks(db, d7),
            "prev_7d": _clicks(db, d14, d7),
            "last_30d": _clicks(db, d30),
            "last_7d_by_shop": _grouped_clicks(db, models.AffiliateClick.shop, d7),
            "last_7d_by_placement": _grouped_clicks(db, models.AffiliateClick.placement, d7),
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
        "optimization_actions_last_30d": [
            {"type": t, "verdict": v or "not_evaluated", "count": c} for t, v, c in actions
        ],
    }
