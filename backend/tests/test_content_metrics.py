import datetime

from sqlalchemy import select

from app import analytics_ga4, content_metrics, crud, models, schemas, search_console


def _make_product(db, slug="ping-g440-max", name="G440 MAX ドライバー"):
    return crud.create_product(
        db, schemas.ProductCreate(name=name, brand="PING", category="driver", model_number=name, slug=slug)
    )


def test_capture_daily_snapshot_noops_when_neither_source_configured(db_session, monkeypatch):
    monkeypatch.setattr(analytics_ga4, "get_top_pages", lambda **kwargs: (_ for _ in ()).throw(analytics_ga4.GA4NotConfigured()))
    monkeypatch.setattr(
        search_console,
        "get_page_performance",
        lambda **kwargs: (_ for _ in ()).throw(search_console.SearchConsoleNotConfigured()),
    )

    result = content_metrics.capture_daily_snapshot(db_session)
    assert result.ga4_available is False
    assert result.search_console_available is False
    assert result.pages_captured == 0

    rows = list(db_session.execute(select(models.PageMetricsSnapshot)).scalars())
    assert rows == []


def test_capture_daily_snapshot_merges_ga4_and_search_console_by_path(db_session, monkeypatch):
    product = _make_product(db_session)

    monkeypatch.setattr(
        analytics_ga4,
        "get_top_pages",
        lambda **kwargs: [
            analytics_ga4.PageStat(
                path=f"/products/{product.slug}", pageviews=120, active_users=80, bounce_rate=0.4, avg_engagement_seconds=30.0
            )
        ],
    )
    monkeypatch.setattr(
        search_console,
        "get_page_performance",
        lambda **kwargs: [
            search_console.PagePerformance(
                path=f"/products/{product.slug}", clicks=12, impressions=340, ctr=0.035, position=8.4
            )
        ],
    )

    result = content_metrics.capture_daily_snapshot(db_session)
    assert result.ga4_available is True
    assert result.search_console_available is True
    assert result.pages_captured == 1

    row = db_session.execute(select(models.PageMetricsSnapshot)).scalar_one()
    assert row.path == f"/products/{product.slug}"
    assert row.product_id == product.id
    assert row.pageviews == 120
    assert row.search_clicks == 12
    assert row.search_ctr == 0.035
    assert row.snapshot_date == datetime.date.today()


def test_capture_daily_snapshot_matches_guide_slug(db_session, monkeypatch):
    monkeypatch.setattr(
        analytics_ga4,
        "get_top_pages",
        lambda **kwargs: [
            analytics_ga4.PageStat(
                path="/guides/iron-set-comparison", pageviews=50, active_users=40, bounce_rate=0.5, avg_engagement_seconds=20.0
            )
        ],
    )
    monkeypatch.setattr(search_console, "get_page_performance", lambda **kwargs: [])

    content_metrics.capture_daily_snapshot(db_session)

    row = db_session.execute(select(models.PageMetricsSnapshot)).scalar_one()
    assert row.guide_slug == "iron-set-comparison"
    assert row.product_id is None


def test_capture_daily_snapshot_uses_whichever_single_source_is_configured(db_session, monkeypatch):
    monkeypatch.setattr(
        analytics_ga4,
        "get_top_pages",
        lambda **kwargs: [
            analytics_ga4.PageStat(path="/", pageviews=500, active_users=300, bounce_rate=0.3, avg_engagement_seconds=45.0)
        ],
    )
    monkeypatch.setattr(
        search_console,
        "get_page_performance",
        lambda **kwargs: (_ for _ in ()).throw(search_console.SearchConsoleNotConfigured()),
    )

    result = content_metrics.capture_daily_snapshot(db_session)
    assert result.ga4_available is True
    assert result.search_console_available is False
    assert result.pages_captured == 1

    row = db_session.execute(select(models.PageMetricsSnapshot)).scalar_one()
    assert row.pageviews == 500
    assert row.search_clicks is None


def test_capture_daily_snapshot_rerunning_same_day_overwrites_not_duplicates(db_session, monkeypatch):
    monkeypatch.setattr(
        analytics_ga4,
        "get_top_pages",
        lambda **kwargs: [
            analytics_ga4.PageStat(path="/", pageviews=100, active_users=60, bounce_rate=0.3, avg_engagement_seconds=30.0)
        ],
    )
    monkeypatch.setattr(search_console, "get_page_performance", lambda **kwargs: [])

    content_metrics.capture_daily_snapshot(db_session)

    monkeypatch.setattr(
        analytics_ga4,
        "get_top_pages",
        lambda **kwargs: [
            analytics_ga4.PageStat(path="/", pageviews=150, active_users=90, bounce_rate=0.25, avg_engagement_seconds=35.0)
        ],
    )
    content_metrics.capture_daily_snapshot(db_session)

    rows = list(db_session.execute(select(models.PageMetricsSnapshot)).scalars())
    assert len(rows) == 1
    assert rows[0].pageviews == 150
