import datetime

import pytest

from app import crud, daily_report, email, models, schemas


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


def test_build_daily_report_says_no_optimization_when_none_happened(db_session):
    subject, html = daily_report.build_daily_report(db_session)
    assert "本日は自動改善の対象がありませんでした" in html


def test_build_daily_report_lists_todays_optimization_actions(db_session):
    product = _make_product(db_session)
    db_session.add(
        models.AiOptimizationAction(
            action_type="rewrite_product",
            target_path=f"/products/{product.slug}",
            product_id=product.id,
            decision_basis="CTRが平均より40%低下",
            status="applied",
        )
    )
    db_session.commit()

    subject, html = daily_report.build_daily_report(db_session)
    assert "商品説明のリライト" in html
    assert f"/products/{product.slug}" in html
    assert "CTRが平均より40%低下" in html


def test_build_daily_report_flags_a_worse_effect_verdict(db_session):
    product = _make_product(db_session)
    action = models.AiOptimizationAction(
        action_type="rewrite_product",
        target_path=f"/products/{product.slug}",
        product_id=product.id,
        decision_basis="x",
        status="applied",
    )
    db_session.add(action)
    db_session.commit()
    action.created_at = datetime.datetime.utcnow() - datetime.timedelta(days=10)
    action.effect_evaluated_at = datetime.datetime.utcnow() - datetime.timedelta(hours=2)
    action.effect_summary = "ページビューが100件→60件（-40%）"
    action.effect_verdict = "worse"
    db_session.commit()

    subject, html = daily_report.build_daily_report(db_session)
    assert "過去の変更の効果測定" in html
    assert "ページビューが100件→60件" in html
    assert "悪化と判定されました" in html


def test_build_daily_report_reports_an_auto_reverted_change_as_done(db_session):
    product = _make_product(db_session)
    action = models.AiOptimizationAction(
        action_type="rewrite_product",
        target_path=f"/products/{product.slug}",
        product_id=product.id,
        decision_basis="x",
        status="reverted",
        revert_reason="auto_worse",
    )
    db_session.add(action)
    db_session.commit()
    action.created_at = datetime.datetime.utcnow() - datetime.timedelta(days=10)
    action.effect_evaluated_at = datetime.datetime.utcnow() - datetime.timedelta(hours=2)
    action.effect_summary = "ページビューが100件→40件（-60%） → 悪化と判定したため自動で元に戻し"
    action.effect_verdict = "worse"
    db_session.commit()

    subject, html = daily_report.build_daily_report(db_session)
    assert "1件は悪化と判定したため自動で元に戻し" in html
    assert "自動では戻していません" not in html


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
    assert "エラーは1件" in html


def test_build_daily_report_no_errors_says_stable(db_session):
    subject, html = daily_report.build_daily_report(db_session)
    assert "エラーは0件" in html


def test_errors_are_grouped_by_cause_across_products(db_session):
    a = _make_product(db_session, name="ドライバーA")
    b = _make_product(db_session, name="アイアンB")
    for p in (a, b):
        crud.create_error_log(db_session, source="price_fetch", message=f"{p.name}: ReadTimeout", product_id=p.id)
    crud.create_error_log(db_session, source="ai_generation", message="Claude API 529 overloaded", level="error")
    subject, html = daily_report.build_daily_report(db_session)
    assert "エラーは3件" in html
    assert "「〈商品〉: ReadTimeout」2件" in html
    assert "エラーの最多原因：価格取得（楽天）の「〈商品〉: ReadTimeout」（2件）" in html


def test_old_errors_are_not_counted(db_session):
    log = crud.create_error_log(db_session, source="price_fetch", message="古いエラー", level="error")
    log.created_at = datetime.datetime.utcnow() - datetime.timedelta(days=3)
    db_session.commit()
    subject, html = daily_report.build_daily_report(db_session)
    assert "エラーは0件" in html


def test_no_clicks_all_week_is_reported_as_a_traffic_problem(db_session):
    subject, html = daily_report.build_daily_report(db_session)
    assert "直近7日間、どのショップへのクリックもありません" in html
    assert "へのクリックが未記録です" not in html


def test_shop_missing_for_a_week_is_named(db_session):
    product = _make_product(db_session)
    _click(db_session, product.id, "amazon", hours_ago=50)
    _click(db_session, product.id, "rakuten", hours_ago=100)
    subject, html = daily_report.build_daily_report(db_session)
    assert "Yahoo!は直近7日間のクリックが0件です（3ショップ合計は2件）" in html


def test_missing_yahoo_affiliate_ids_are_flagged(db_session, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "yahoo_affiliate_id", "")
    subject, html = daily_report.build_daily_report(db_session)
    assert "アフィリエイト未設定" in html


def test_build_daily_report_includes_manual_x_post_text_when_a_deal_qualifies(db_session):
    product = _make_product(db_session)
    product.buy_score = "strong_buy"
    product.buy_signal_score = 90
    product.history_span_days = 14
    product.msrp = 60000
    product.current_price = 45000
    db_session.commit()

    subject, html = daily_report.build_daily_report(db_session)
    assert "X投稿用テキスト" in html
    assert "#ゴルフ" in html


def test_build_daily_report_says_no_deal_when_nothing_qualifies(db_session):
    subject, html = daily_report.build_daily_report(db_session)
    assert "本日は投稿対象となる商品がありません" in html


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


def test_build_daily_report_includes_the_self_heal_summary(db_session):
    from app import self_heal

    self_heal.heal(db_session, since_id=0)
    subject, html = daily_report.build_daily_report(db_session)
    assert "【自動修復】確認したエラー0件。" in html
