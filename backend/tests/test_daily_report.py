import datetime

import pytest

from app import crud, daily_report, email, schemas


def _make_product(db_session, name="テスト用ドライバー", brand="TestBrand", category="driver"):
    return crud.create_product(
        db_session,
        schemas.ProductCreate(name=name, brand=brand, category=category, model_number=name),
    )


def _click(db_session, product_id, shop, hours_ago):
    click = crud.create_affiliate_click(
        db_session, schemas.AffiliateClickCreate(product_id=product_id, shop=shop, placement="product_detail_cta")
    )
    click.created_at = datetime.datetime.utcnow() - datetime.timedelta(hours=hours_ago)
    db_session.commit()
    return click


def test_build_daily_report_with_no_data(db_session):
    subject, html = daily_report.build_daily_report(db_session)
    assert "本日のAI会議レポート" in subject
    assert "直近24時間で0件" in html
    assert "実データ" in html


def test_build_daily_report_reflects_real_click_trend(db_session):
    product = _make_product(db_session)
    _click(db_session, product.id, "amazon", hours_ago=2)
    _click(db_session, product.id, "amazon", hours_ago=3)
    _click(db_session, product.id, "rakuten", hours_ago=5)
    # yesterday: 1 click total, so today's 3 is a real increase
    _click(db_session, product.id, "amazon", hours_ago=30)

    subject, html = daily_report.build_daily_report(db_session)
    assert "直近24時間で3件" in html
    assert "Amazon 2件" in html
    assert "楽天 1件" in html
    assert "前日比 +2件" in html


def test_build_daily_report_flags_real_errors(db_session):
    crud.create_error_log(db_session, source="price_fetch", message="エラー発生", level="error")
    subject, html = daily_report.build_daily_report(db_session)
    assert "エラーが1件" in html


def test_build_daily_report_no_errors_says_stable(db_session):
    subject, html = daily_report.build_daily_report(db_session)
    assert "エラーは見当たりません" in html


def test_build_daily_report_includes_daily_job_summary(db_session):
    crud.create_error_log(
        db_session, source="daily_job", level="info", message="日次更新ジョブ完了: 楽天更新3件/スキップ0件"
    )
    subject, html = daily_report.build_daily_report(db_session)
    assert "楽天更新3件/スキップ0件" in html


def test_send_daily_report_raises_when_email_not_configured(db_session, monkeypatch):
    monkeypatch.setenv("DAILY_REPORT_EMAIL", "")
    from app.config import get_settings

    get_settings.cache_clear()
    with pytest.raises(daily_report.DailyReportNotConfigured):
        daily_report.send_daily_report(db_session)
    get_settings.cache_clear()


def test_send_daily_report_sends_via_resend_when_configured(db_session, monkeypatch):
    monkeypatch.setenv("DAILY_REPORT_EMAIL", "owner@example.com")
    from app.config import get_settings

    get_settings.cache_clear()

    sent_calls = []
    monkeypatch.setattr(email, "send_email", lambda **kwargs: sent_calls.append(kwargs))

    daily_report.send_daily_report(db_session)

    assert len(sent_calls) == 1
    assert sent_calls[0]["to"] == "owner@example.com"
    assert "本日のAI会議レポート" in sent_calls[0]["subject"]
    get_settings.cache_clear()


def test_send_daily_report_endpoint_requires_admin_auth(client):
    resp = client.post("/api/admin/send-daily-report")
    assert resp.status_code in (401, 403)


def test_send_daily_report_endpoint_400_when_not_configured(client, admin_headers, monkeypatch):
    monkeypatch.setenv("DAILY_REPORT_EMAIL", "")
    from app.config import get_settings

    get_settings.cache_clear()
    resp = client.post("/api/admin/send-daily-report", headers=admin_headers)
    assert resp.status_code == 400
    get_settings.cache_clear()


def test_send_daily_report_endpoint_sends_when_configured(client, admin_headers, monkeypatch):
    monkeypatch.setenv("DAILY_REPORT_EMAIL", "owner@example.com")
    from app.config import get_settings

    get_settings.cache_clear()

    sent_calls = []
    monkeypatch.setattr(email, "send_email", lambda **kwargs: sent_calls.append(kwargs))

    resp = client.post("/api/admin/send-daily-report", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json() == {"sent": True}
    assert len(sent_calls) == 1
    get_settings.cache_clear()
