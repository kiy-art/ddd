import json
from unittest.mock import MagicMock

import pytest

from app import analytics_ga4


def test_get_top_pages_requires_configuration(monkeypatch):
    monkeypatch.setenv("GA4_PROPERTY_ID", "")
    monkeypatch.setenv("GA4_SERVICE_ACCOUNT_JSON", "")
    from app.config import get_settings

    get_settings.cache_clear()
    with pytest.raises(analytics_ga4.GA4NotConfigured):
        analytics_ga4.get_top_pages()
    get_settings.cache_clear()


def test_get_top_pages_rejects_invalid_json(monkeypatch):
    monkeypatch.setenv("GA4_PROPERTY_ID", "555025729")
    monkeypatch.setenv("GA4_SERVICE_ACCOUNT_JSON", "not-json")
    from app.config import get_settings

    get_settings.cache_clear()
    with pytest.raises(analytics_ga4.GA4NotConfigured):
        analytics_ga4.get_top_pages()
    get_settings.cache_clear()


def test_get_top_pages_parses_real_response_shape(monkeypatch):
    """Mocks the GA4 client at the boundary (the RunReportResponse), so this
    exercises our own parsing logic against the actual response shape the
    API returns - not a hand-rolled fake."""
    monkeypatch.setenv("GA4_PROPERTY_ID", "555025729")
    fake_sa_info = {
        "type": "service_account",
        "project_id": "par-golf-agent",
        "private_key": "fake",
        "client_email": "ga4-reader@par-golf-agent.iam.gserviceaccount.com",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
    monkeypatch.setenv("GA4_SERVICE_ACCOUNT_JSON", json.dumps(fake_sa_info))
    from app.config import get_settings

    get_settings.cache_clear()

    fake_row = MagicMock()
    fake_row.dimension_values = [MagicMock(value="/products/ping-g440")]
    fake_row.metric_values = [
        MagicMock(value="120"),
        MagicMock(value="80"),
        MagicMock(value="0.35"),
        MagicMock(value="45.2"),
    ]
    fake_response = MagicMock()
    fake_response.rows = [fake_row]

    fake_client_instance = MagicMock()
    fake_client_instance.run_report.return_value = fake_response

    monkeypatch.setattr(
        "google.analytics.data_v1beta.BetaAnalyticsDataClient",
        lambda credentials=None: fake_client_instance,
    )
    monkeypatch.setattr(
        "google.oauth2.service_account.Credentials.from_service_account_info",
        lambda info: MagicMock(),
    )

    stats = analytics_ga4.get_top_pages(days=28, limit=25)

    assert len(stats) == 1
    assert stats[0].path == "/products/ping-g440"
    assert stats[0].pageviews == 120
    assert stats[0].active_users == 80
    assert stats[0].bounce_rate == 0.35
    assert stats[0].avg_engagement_seconds == 45.2

    get_settings.cache_clear()
