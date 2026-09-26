"""Read-only client for the Google Search Console API (searchanalytics).

Gives real per-page and per-query click/impression/CTR/position numbers -
the "検索でどれだけ見つかっている/クリックされているか" signal that GA4
(app/analytics_ga4.py) doesn't provide (GA4 only knows what happened once
someone lands on the site, not how it performed in the search results
themselves). Used by app/content_metrics.py (daily snapshot capture) and
app/content_optimizer.py (rising-query detection for new guide drafts).

Reuses the same GCP service account as GA4_SERVICE_ACCOUNT_JSON - that
account's email additionally needs to be added as a user on the Search
Console property (Settings > Users and permissions in Search Console),
a separate one-time grant from GA4 property access. See README.
"""

import dataclasses
import datetime
import json

from app.config import get_settings


class SearchConsoleNotConfigured(Exception):
    pass


@dataclasses.dataclass
class PagePerformance:
    path: str
    clicks: int
    impressions: int
    ctr: float  # 0-1
    position: float  # average search result position, 1-based


@dataclasses.dataclass
class QueryPerformance:
    query: str
    clicks: int
    impressions: int
    ctr: float
    position: float


def _client_and_site():
    settings = get_settings()
    if not settings.ga4_service_account_json or not settings.search_console_site_url:
        raise SearchConsoleNotConfigured(
            "GA4_SERVICE_ACCOUNT_JSON / SEARCH_CONSOLE_SITE_URL is not configured"
        )

    # Imported lazily, same reasoning as analytics_ga4.get_top_pages: avoid
    # paying this import's cost on every request that doesn't touch Search
    # Console.
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    try:
        info = json.loads(settings.ga4_service_account_json)
    except json.JSONDecodeError as exc:
        raise SearchConsoleNotConfigured(f"GA4_SERVICE_ACCOUNT_JSON is not valid JSON: {exc}") from exc

    credentials = service_account.Credentials.from_service_account_info(
        info, scopes=["https://www.googleapis.com/auth/webmasters.readonly"]
    )
    service = build("searchconsole", "v1", credentials=credentials)
    return service, settings.search_console_site_url


def _date_range(days: int) -> tuple[str, str]:
    end = datetime.date.today()
    start = end - datetime.timedelta(days=days)
    return start.isoformat(), end.isoformat()


def get_page_performance(days: int = 28, limit: int = 25) -> list[PagePerformance]:
    """Real click/impression/CTR/position per page over the last `days`
    days - the basis for "このページの検索経由のクリック率が落ちている" as
    an actual checkable claim rather than a guess."""
    service, site_url = _client_and_site()
    start_date, end_date = _date_range(days)

    response = (
        service.searchanalytics()
        .query(
            siteUrl=site_url,
            body={
                "startDate": start_date,
                "endDate": end_date,
                "dimensions": ["page"],
                "rowLimit": limit,
                "orderBy": [{"metric": "impressions", "sortOrder": "descending"}],
            },
        )
        .execute()
    )

    results = []
    for row in response.get("rows", []):
        path = row["keys"][0]
        results.append(
            PagePerformance(
                path=path,
                clicks=int(row.get("clicks", 0)),
                impressions=int(row.get("impressions", 0)),
                ctr=round(float(row.get("ctr", 0.0)), 4),
                position=round(float(row.get("position", 0.0)), 1),
            )
        )
    return results


def get_top_queries(days: int = 28, limit: int = 25) -> list[QueryPerformance]:
    """Real search queries actually driving impressions/clicks to the
    site - the honest substitute for "検索トレンドを分析" (there is no
    external search-demand/trend API integrated; this is only what people
    are actually searching that surfaces this site, not a global trend)."""
    service, site_url = _client_and_site()
    start_date, end_date = _date_range(days)

    response = (
        service.searchanalytics()
        .query(
            siteUrl=site_url,
            body={
                "startDate": start_date,
                "endDate": end_date,
                "dimensions": ["query"],
                "rowLimit": limit,
                "orderBy": [{"metric": "impressions", "sortOrder": "descending"}],
            },
        )
        .execute()
    )

    results = []
    for row in response.get("rows", []):
        query = row["keys"][0]
        results.append(
            QueryPerformance(
                query=query,
                clicks=int(row.get("clicks", 0)),
                impressions=int(row.get("impressions", 0)),
                ctr=round(float(row.get("ctr", 0.0)), 4),
                position=round(float(row.get("position", 0.0)), 1),
            )
        )
    return results


def get_queries_for_page(page_url: str, days: int = 28, limit: int = 5) -> list[QueryPerformance]:
    """The real queries a single page already appears for - what a
    search-CTR rewrite should align its title with (search intent the page
    is actually being shown for), rather than guessed keywords."""
    service, site_url = _client_and_site()
    start_date, end_date = _date_range(days)

    response = (
        service.searchanalytics()
        .query(
            siteUrl=site_url,
            body={
                "startDate": start_date,
                "endDate": end_date,
                "dimensions": ["query"],
                "dimensionFilterGroups": [
                    {"filters": [{"dimension": "page", "operator": "equals", "expression": page_url}]}
                ],
                "rowLimit": limit,
                "orderBy": [{"metric": "impressions", "sortOrder": "descending"}],
            },
        )
        .execute()
    )

    return [
        QueryPerformance(
            query=row["keys"][0],
            clicks=int(row.get("clicks", 0)),
            impressions=int(row.get("impressions", 0)),
            ctr=round(float(row.get("ctr", 0.0)), 4),
            position=round(float(row.get("position", 0.0)), 1),
        )
        for row in response.get("rows", [])
    ]
