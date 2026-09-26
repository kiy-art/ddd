"""Captures one real, dated PageMetricsSnapshot row per page per day from
GA4 (pageviews/bounce/engagement) and Search Console (search clicks/
impressions/CTR/position) - see app/models.py's PageMetricsSnapshot for why
this history is what makes "this page is declining" a checkable claim
instead of a single-point-in-time guess.

A no-op (returns an empty result, never raises) when neither GA4 nor
Search Console is configured - same "optional integration" treatment as
every other external API in this codebase (yahoo_client_id, resend_api_key,
etc). Uses whichever of the two IS configured if only one is.
"""

import dataclasses
import datetime
import re
import urllib.parse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import analytics_ga4, models, search_console

# GA4's own rolling-window report (see analytics_ga4.get_top_pages) is read
# with a short window each run so a day's snapshot approximates that day's
# traffic rather than a blurred 28-day average. Search Console's own data
# typically lags 1-3 days behind real time, so a longer window is used
# there and stored under today's snapshot_date as "most recent available"
# search performance, not a literal single day - approximate by nature,
# same spirit as x_post.py's weighted-character-count comment.
GA4_WINDOW_DAYS = 1
SEARCH_CONSOLE_WINDOW_DAYS = 3
SNAPSHOT_PAGE_LIMIT = 100

_PRODUCT_PATH_RE = re.compile(r"^/products/([^/?#]+)")
_GUIDE_PATH_RE = re.compile(r"^/guides/([^/?#]+)")


@dataclasses.dataclass
class SnapshotCaptureResult:
    ga4_available: bool
    search_console_available: bool
    pages_captured: int


def _normalize_path(path_or_url: str) -> str:
    # GA4 reports a bare path ("/products/x"), but Search Console reports
    # the page's full URL ("https://par-gear.com/products/x") - both must
    # reduce to the same key or the two sources never merge into one row.
    path = urllib.parse.urlparse(path_or_url).path or "/"
    return path.rstrip("/") or "/"


def _match_product_id(path: str, slug_to_id: dict[str, int]) -> int | None:
    m = _PRODUCT_PATH_RE.match(path)
    return slug_to_id.get(m.group(1)) if m else None


def _match_guide_slug(path: str) -> str | None:
    m = _GUIDE_PATH_RE.match(path)
    return m.group(1) if m else None


def capture_daily_snapshot(db: Session) -> SnapshotCaptureResult:
    """Idempotent within a day: re-running overwrites today's row for a
    given path with the latest pull rather than creating a duplicate (the
    (snapshot_date, path) unique constraint is enforced in code here, not
    left to the DB to reject, since SQLite/Postgres upsert syntax differs
    and this project avoids DB-specific SQL - see other crud.py functions)."""
    ga4_pages: dict[str, analytics_ga4.PageStat] = {}
    ga4_available = True
    try:
        for stat in analytics_ga4.get_top_pages(days=GA4_WINDOW_DAYS, limit=SNAPSHOT_PAGE_LIMIT):
            ga4_pages[_normalize_path(stat.path)] = stat
    except analytics_ga4.GA4NotConfigured:
        ga4_available = False

    search_pages: dict[str, search_console.PagePerformance] = {}
    search_console_available = True
    try:
        for stat in search_console.get_page_performance(days=SEARCH_CONSOLE_WINDOW_DAYS, limit=SNAPSHOT_PAGE_LIMIT):
            search_pages[_normalize_path(stat.path)] = stat
    except search_console.SearchConsoleNotConfigured:
        search_console_available = False

    all_paths = set(ga4_pages) | set(search_pages)
    if not all_paths:
        return SnapshotCaptureResult(ga4_available, search_console_available, 0)

    slug_to_id = {
        slug: pid
        for pid, slug in db.execute(select(models.Product.id, models.Product.slug)).all()
    }
    today = datetime.date.today()

    existing = {
        row.path: row
        for row in db.execute(
            select(models.PageMetricsSnapshot).where(models.PageMetricsSnapshot.snapshot_date == today)
        ).scalars()
    }

    captured = 0
    for path in all_paths:
        row = existing.get(path)
        if row is None:
            row = models.PageMetricsSnapshot(
                snapshot_date=today,
                path=path,
                product_id=_match_product_id(path, slug_to_id),
                guide_slug=_match_guide_slug(path),
            )
            db.add(row)

        ga4_stat = ga4_pages.get(path)
        if ga4_stat is not None:
            row.pageviews = ga4_stat.pageviews
            row.active_users = ga4_stat.active_users
            row.bounce_rate = ga4_stat.bounce_rate
            row.avg_engagement_seconds = ga4_stat.avg_engagement_seconds

        search_stat = search_pages.get(path)
        if search_stat is not None:
            row.search_clicks = search_stat.clicks
            row.search_impressions = search_stat.impressions
            row.search_ctr = search_stat.ctr
            row.search_position = search_stat.position

        captured += 1

    db.commit()
    return SnapshotCaptureResult(ga4_available, search_console_available, captured)
