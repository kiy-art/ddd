import json
from unittest.mock import MagicMock

import pytest

from app import search_console


def _set_env(monkeypatch, site_url="sc-domain:par-gear.com"):
    fake_sa_info = {
        "type": "service_account",
        "project_id": "par-golf-agent",
        "private_key": "fake",
        "client_email": "ga4-reader@par-golf-agent.iam.gserviceaccount.com",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
    monkeypatch.setenv("GA4_SERVICE_ACCOUNT_JSON", json.dumps(fake_sa_info))
    monkeypatch.setenv("SEARCH_CONSOLE_SITE_URL", site_url)
    from app.config import get_settings

    get_settings.cache_clear()


def test_get_page_performance_requires_configuration(monkeypatch):
    monkeypatch.setenv("GA4_SERVICE_ACCOUNT_JSON", "")
    monkeypatch.setenv("SEARCH_CONSOLE_SITE_URL", "")
    from app.config import get_settings

    get_settings.cache_clear()
    with pytest.raises(search_console.SearchConsoleNotConfigured):
        search_console.get_page_performance()
    get_settings.cache_clear()


def test_get_page_performance_rejects_invalid_json(monkeypatch):
    monkeypatch.setenv("GA4_SERVICE_ACCOUNT_JSON", "not-json")
    monkeypatch.setenv("SEARCH_CONSOLE_SITE_URL", "sc-domain:par-gear.com")
    from app.config import get_settings

    get_settings.cache_clear()
    with pytest.raises(search_console.SearchConsoleNotConfigured):
        search_console.get_page_performance()
    get_settings.cache_clear()


def _mock_build(fake_service):
    return lambda *args, **kwargs: fake_service


def test_get_page_performance_parses_real_response_shape(monkeypatch):
    _set_env(monkeypatch)

    fake_response = {
        "rows": [
            {"keys": ["/products/ping-g440"], "clicks": 12, "impressions": 340, "ctr": 0.0353, "position": 8.4}
        ]
    }
    fake_query = MagicMock()
    fake_query.execute.return_value = fake_response
    fake_service = MagicMock()
    fake_service.searchanalytics.return_value.query.return_value = fake_query

    monkeypatch.setattr("googleapiclient.discovery.build", _mock_build(fake_service))
    monkeypatch.setattr(
        "google.oauth2.service_account.Credentials.from_service_account_info",
        lambda info, **kwargs: MagicMock(),
    )

    stats = search_console.get_page_performance(days=28, limit=25)

    assert len(stats) == 1
    assert stats[0].path == "/products/ping-g440"
    assert stats[0].clicks == 12
    assert stats[0].impressions == 340
    assert stats[0].ctr == 0.0353
    assert stats[0].position == 8.4

    call_kwargs = fake_service.searchanalytics.return_value.query.call_args.kwargs
    assert call_kwargs["siteUrl"] == "sc-domain:par-gear.com"
    assert call_kwargs["body"]["dimensions"] == ["page"]


def test_get_top_queries_parses_real_response_shape(monkeypatch):
    _set_env(monkeypatch)

    fake_response = {
        "rows": [
            {"keys": ["ping g440 中古"], "clicks": 3, "impressions": 90, "ctr": 0.0333, "position": 12.1}
        ]
    }
    fake_query = MagicMock()
    fake_query.execute.return_value = fake_response
    fake_service = MagicMock()
    fake_service.searchanalytics.return_value.query.return_value = fake_query

    monkeypatch.setattr("googleapiclient.discovery.build", _mock_build(fake_service))
    monkeypatch.setattr(
        "google.oauth2.service_account.Credentials.from_service_account_info",
        lambda info, **kwargs: MagicMock(),
    )

    stats = search_console.get_top_queries(days=28, limit=25)

    assert len(stats) == 1
    assert stats[0].query == "ping g440 中古"
    assert stats[0].clicks == 3
    assert stats[0].impressions == 90

    call_kwargs = fake_service.searchanalytics.return_value.query.call_args.kwargs
    assert call_kwargs["body"]["dimensions"] == ["query"]


def test_get_queries_for_page_filters_by_the_exact_page_url(monkeypatch):
    _set_env(monkeypatch, site_url="https://par-gear.com/")

    fake_query = MagicMock()
    fake_query.execute.return_value = {
        "rows": [{"keys": ["g440 max 値下がり"], "clicks": 1, "impressions": 80, "ctr": 0.0125, "position": 9.2}]
    }
    fake_service = MagicMock()
    fake_service.searchanalytics.return_value.query.return_value = fake_query

    monkeypatch.setattr("googleapiclient.discovery.build", _mock_build(fake_service))
    monkeypatch.setattr(
        "google.oauth2.service_account.Credentials.from_service_account_info",
        lambda info, **kwargs: MagicMock(),
    )

    rows = search_console.get_queries_for_page("https://par-gear.com/products/ping-g440-max")
    assert [r.query for r in rows] == ["g440 max 値下がり"]

    body = fake_service.searchanalytics.return_value.query.call_args.kwargs["body"]
    assert body["dimensionFilterGroups"][0]["filters"][0] == {
        "dimension": "page",
        "operator": "equals",
        "expression": "https://par-gear.com/products/ping-g440-max",
    }
