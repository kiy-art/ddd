"""Read-only client for the Google Analytics Data API (GA4).

Used only for on-demand analysis (an admin asks "look at analytics and
suggest improvements" in a Claude Code session) - there is no automated
daily job. Credentials are a Viewer-scoped GCP service account, configured
via Render environment variables, never committed or logged.
"""

import dataclasses
import json

from app.config import get_settings


class GA4NotConfigured(Exception):
    pass


@dataclasses.dataclass
class PageStat:
    path: str
    pageviews: int
    active_users: int
    bounce_rate: float  # 0-1
    avg_engagement_seconds: float


def get_top_pages(days: int = 28, limit: int = 25) -> list[PageStat]:
    """Top pages by pageviews over the last `days` days, with bounce rate
    and average engagement time - the real data behind "find popular
    pages" / "analyze drop-off" (no fabricated numbers)."""
    settings = get_settings()
    if not settings.ga4_property_id or not settings.ga4_service_account_json:
        raise GA4NotConfigured("GA4_PROPERTY_ID / GA4_SERVICE_ACCOUNT_JSON is not configured")

    # Imported lazily: this pulls in grpc/protobuf, which we don't want to
    # pay the import cost for on every backend request that doesn't touch GA4.
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import DateRange, Dimension, Metric, OrderBy, RunReportRequest
    from google.oauth2 import service_account

    try:
        info = json.loads(settings.ga4_service_account_json)
    except json.JSONDecodeError as exc:
        raise GA4NotConfigured(f"GA4_SERVICE_ACCOUNT_JSON is not valid JSON: {exc}") from exc

    credentials = service_account.Credentials.from_service_account_info(info)
    client = BetaAnalyticsDataClient(credentials=credentials)

    request = RunReportRequest(
        property=f"properties/{settings.ga4_property_id}",
        dimensions=[Dimension(name="pagePath")],
        metrics=[
            Metric(name="screenPageViews"),
            Metric(name="activeUsers"),
            Metric(name="bounceRate"),
            Metric(name="averageSessionDuration"),
        ],
        date_ranges=[DateRange(start_date=f"{days}daysAgo", end_date="today")],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="screenPageViews"), desc=True)],
        limit=limit,
    )
    response = client.run_report(request)

    stats = []
    for row in response.rows:
        stats.append(
            PageStat(
                path=row.dimension_values[0].value,
                pageviews=int(float(row.metric_values[0].value)),
                active_users=int(float(row.metric_values[1].value)),
                bounce_rate=round(float(row.metric_values[2].value), 4),
                avg_engagement_seconds=round(float(row.metric_values[3].value), 1),
            )
        )
    return stats
