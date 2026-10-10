import datetime

from sqlalchemy import select

from app import crud, models, pipeline, schemas, self_heal


def _product(db, name="G430 Iron", brand="PING"):
    return crud.create_product(db, schemas.ProductCreate(name=name, brand=brand, category="iron", initial_price=60000))


def _log(db, source, message, level="error", product_id=None, days_ago=None):
    row = crud.create_error_log(db, source=source, message=message, level=level, product_id=product_id)
    if days_ago is not None:
        row.created_at = datetime.datetime.utcnow() - datetime.timedelta(days=days_ago)
        db.commit()
    return row


def _summary_rows(db):
    return db.execute(select(models.ErrorLog).where(models.ErrorLog.source == "self_heal")).scalars().all()


class _Recorder:
    def __init__(self, returns):
        self.calls = []
        self.returns = returns

    def __call__(self, db, **kwargs):
        self.calls.append(kwargs)
        return self.returns


# --- classification ---------------------------------------------------------


def test_classify_setup_quota_and_transient():
    def row(message):
        return models.ErrorLog(source="price_fetch", level="error", message=message)

    assert self_heal.classify(row("G430: Rakuten API 403: forbidden")) == "setup"
    assert self_heal.classify(row("RAKUTEN_ACCESS_KEY is not configured")) == "setup"
    assert self_heal.classify(row("Yahoo: quota exhausted, stopping")) == "quota"
    assert self_heal.classify(row("G430: Rakuten API 429: too many requests")) == "quota"


def test_rakuten_keyword_400_is_not_reported_as_a_setup_problem():
    # STEP74: Rakuten's body carries "wrong_parameter" for a bad keyword too.
    def row(message):
        return models.ErrorLog(source="price_fetch", level="error", message=message)

    bad_keyword = 'G440 K: Rakuten API 400: {"error_description":"keyword is not valid","error":"wrong_parameter"}'
    too_long = 'X: Rakuten API 400: {"error_description":"keyword must be under 128 length","error":"wrong_parameter"}'
    bad_app_id = 'X: Rakuten API 400: {"error_description":"specify valid applicationId","error":"wrong_parameter"}'
    assert self_heal.classify(row(bad_keyword)) == "keyword"
    assert self_heal.classify(row(too_long)) == "keyword"
    assert self_heal.classify(row(bad_app_id)) == "setup"
    assert self_heal.classify(row("G430: ReadTimeout('timed out')")) == "transient"
    assert self_heal.classify(row("G430: Rakuten API 503: unavailable")) == "transient"


# --- remedies ----------------------------------------------------------------


def test_retries_only_this_runs_transient_rakuten_failures(db_session, monkeypatch):
    old, fresh, bad_key = _product(db_session, "Old"), _product(db_session, "Fresh"), _product(db_session, "Key")
    _log(db_session, "price_fetch", "Old: ReadTimeout", product_id=old.id)
    since = self_heal.latest_watermark(db_session)
    _log(db_session, "price_fetch", "Fresh: ReadTimeout", product_id=fresh.id)
    _log(db_session, "price_fetch", "Key: Rakuten API 403: forbidden", product_id=bad_key.id)
    rakuten = _Recorder((1, 0))
    monkeypatch.setattr(pipeline, "fetch_rakuten_prices", rakuten)

    result = self_heal.heal(db_session, since_id=since)

    assert rakuten.calls == [{"only_product_ids": [fresh.id]}]  # not the older row, not the setup error
    assert result.refetched_product_ids == [fresh.id]
    assert [(r.label, r.attempted, r.succeeded) for r in result.remedies] == [("楽天の価格再取得", 1, 1)]
    assert result.needs_setup and "RAKUTEN_ACCESS_KEY" in result.needs_setup[0]
    assert result.needs_attention


def test_yahoo_failures_are_retried_only_when_yahoo_is_configured(db_session, monkeypatch):
    product = _product(db_session)
    _log(db_session, "price_fetch", f"Yahoo: {product.name}: ReadTimeout", product_id=product.id)
    yahoo = _Recorder((1, 0))
    monkeypatch.setattr(pipeline, "fetch_yahoo_prices", yahoo)
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        monkeypatch.setenv("YAHOO_CLIENT_ID", "")
        get_settings.cache_clear()
        self_heal.heal(db_session, since_id=0)
        assert yahoo.calls == []

        monkeypatch.setenv("YAHOO_CLIENT_ID", "test-yahoo")
        get_settings.cache_clear()
        result = self_heal.heal(db_session, since_id=0)
        assert yahoo.calls == [{"only_product_ids": [product.id]}]
        assert ("Yahoo!の価格再取得", 1, 1) in [(r.label, r.attempted, r.succeeded) for r in result.remedies]
    finally:
        get_settings.cache_clear()


def test_popularity_failure_reruns_the_sync_and_ignores_the_restatement_row(db_session, monkeypatch):
    _log(db_session, "popularity", "driver: Rakuten API 503: unavailable")
    # the "0 categories" summary names the API keys in its advice text -
    # it must not turn a network failure into a "setup" problem
    _log(db_session, "popularity", "楽天の人気ランキングを1カテゴリも取得できませんでした（5カテゴリ失敗）。RAKUTEN_ACCESS_KEY を確認")
    sync = _Recorder((12, 5))
    monkeypatch.setattr(self_heal.popularity, "sync_popularity_rankings", sync)

    result = self_heal.heal(db_session, since_id=0)

    assert len(sync.calls) == 1
    assert result.needs_setup == []
    assert result.errors_seen == 1
    assert [(r.attempted, r.succeeded) for r in result.remedies] == [(5, 5)]


def test_consumables_failure_reruns_the_refresh(db_session, monkeypatch):
    _log(db_session, "consumables", "Consumables refresh failed: ConnectError")
    refresh = _Recorder((6, 1))
    monkeypatch.setattr(self_heal.consumables_merchandiser, "refresh_consumable_prices", refresh)
    result = self_heal.heal(db_session, since_id=0)
    assert len(refresh.calls) == 1
    assert [(r.label, r.succeeded) for r in result.remedies] == [("消耗品の価格再取得", 1)]


def test_errors_without_a_safe_fix_are_reported_never_retried(db_session, monkeypatch):
    _log(db_session, "x_post", "X post failed: ReadTimeout")  # retrying could double-post
    _log(db_session, "analysis", "G430: division by zero")
    rakuten = _Recorder((0, 0))
    monkeypatch.setattr(pipeline, "fetch_rakuten_prices", rakuten)

    result = self_heal.heal(db_session, since_id=0)

    assert rakuten.calls == [] and result.remedies == []
    assert sorted(result.unresolved) == ["X投稿 1件", "商品分析 1件"]
    assert "自動では直せないエラー" in result.summary
    assert _summary_rows(db_session)[-1].level == "warning"


def test_quota_errors_wait_for_tomorrow(db_session, monkeypatch):
    _log(db_session, "price_fetch", "Yahoo: quota exhausted, stopping (40 product(s) skipped this run): 429")
    yahoo = _Recorder((0, 0))
    monkeypatch.setattr(pipeline, "fetch_yahoo_prices", yahoo)
    result = self_heal.heal(db_session, since_id=0)
    assert yahoo.calls == []
    assert result.quota_limited == ["価格取得（Yahoo!）"]
    assert "明日自動で再開" in result.summary


def test_product_retries_are_capped(db_session, monkeypatch):
    for i in range(self_heal.MAX_PRODUCT_RETRIES + 3):
        product = _product(db_session, f"P{i}")
        _log(db_session, "price_fetch", f"P{i}: ReadTimeout", product_id=product.id)
    rakuten = _Recorder((0, 0))
    monkeypatch.setattr(pipeline, "fetch_rakuten_prices", rakuten)
    result = self_heal.heal(db_session, since_id=0)
    assert len(rakuten.calls[0]["only_product_ids"]) == self_heal.MAX_PRODUCT_RETRIES
    assert result.skipped_for_time


def test_no_remedy_starts_once_the_time_budget_is_spent(db_session, monkeypatch):
    product = _product(db_session)
    _log(db_session, "price_fetch", "G430 Iron: ReadTimeout", product_id=product.id)
    rakuten = _Recorder((1, 0))
    monkeypatch.setattr(pipeline, "fetch_rakuten_prices", rakuten)
    ticks = iter([0.0, self_heal.TIME_BUDGET_SECONDS + 1] + [999.0] * 10)
    result = self_heal.heal(db_session, since_id=0, clock=lambda: next(ticks))
    assert rakuten.calls == [] and result.skipped_for_time


def test_a_failing_remedy_is_logged_not_raised(db_session, monkeypatch):
    product = _product(db_session)
    _log(db_session, "price_fetch", "G430 Iron: ReadTimeout", product_id=product.id)

    def _boom(db, **kwargs):
        raise RuntimeError("still down")

    monkeypatch.setattr(pipeline, "fetch_rakuten_prices", _boom)
    result = self_heal.heal(db_session, since_id=0)
    assert [(r.attempted, r.succeeded) for r in result.remedies] == [(1, 0)]
    messages = [r.message for r in _summary_rows(db_session)]
    assert any("still down" in m for m in messages)


# --- repeat failures / summary ----------------------------------------------


def test_products_failing_on_three_different_days_are_flagged(db_session):
    stuck, flaky = _product(db_session, "Stuck"), _product(db_session, "Flaky")
    for days in (0, 2, 4):
        _log(db_session, "price_fetch", "Stuck: 楽天市場で該当商品が見つかりませんでした", level="info", product_id=stuck.id, days_ago=days)
    for days in (0, 1):
        _log(db_session, "price_fetch", "Flaky: ReadTimeout", product_id=flaky.id, days_ago=days)
    # outside the window - doesn't count
    _log(db_session, "price_fetch", "Flaky: ReadTimeout", product_id=flaky.id, days_ago=10)

    result = self_heal.heal(db_session, since_id=self_heal.latest_watermark(db_session))

    assert result.repeat_failures == ["Stuck"]
    assert "商品名の見直しが必要" in result.summary and "Stuck" in result.summary


def test_a_clean_run_writes_an_info_summary(db_session):
    result = self_heal.heal(db_session, since_id=0)
    assert result.summary == "自動修復: 確認したエラー0件。"
    rows = _summary_rows(db_session)
    assert len(rows) == 1 and rows[0].level == "info"


def test_manual_run_starts_after_the_last_summary(db_session, monkeypatch):
    product = _product(db_session)
    _log(db_session, "price_fetch", "G430 Iron: ReadTimeout", product_id=product.id)
    monkeypatch.setattr(pipeline, "fetch_rakuten_prices", _Recorder((1, 0)))
    self_heal.heal(db_session, since_id=self_heal.default_since_id(db_session))
    # already handled - a second manual run finds nothing new
    second = self_heal.heal(db_session, since_id=self_heal.default_since_id(db_session))
    assert second.errors_seen == 0


# --- plumbing -----------------------------------------------------------------


def test_fetch_rakuten_prices_can_be_limited_to_some_products(db_session, monkeypatch):
    a, b = _product(db_session, "AA"), _product(db_session, "BB")
    looked_up = []
    monkeypatch.setattr(pipeline.time, "sleep", lambda s: None)
    monkeypatch.setattr(pipeline, "search_lowest_price", lambda keyword, **_: looked_up.append(keyword))
    pipeline.fetch_rakuten_prices(db_session, only_product_ids=[b.id])
    assert looked_up == ["PING BB"]
    assert a.id != b.id


def test_self_heal_endpoint_requires_admin(client):
    assert client.post("/api/admin/self-heal").status_code in (401, 403)


def test_self_heal_endpoint_reports_and_reanalyses_refetched_products(client, admin_headers, db_session, monkeypatch):
    product = _product(db_session)
    _log(db_session, "price_fetch", "G430 Iron: ReadTimeout", product_id=product.id)
    monkeypatch.setattr(pipeline, "fetch_rakuten_prices", _Recorder((1, 0)))
    analysed = []
    monkeypatch.setattr(pipeline, "sync_product_analysis", lambda db, p: analysed.append(p.id))

    resp = client.post("/api/admin/self-heal", headers=admin_headers)

    assert resp.status_code == 200
    body = resp.json()
    assert (body["errors_seen"], body["retried"], body["fixed"]) == (1, 1, 1)
    assert body["summary"].startswith("自動修復:")
    assert analysed == [product.id]


def test_daily_job_heals_a_transient_price_failure_in_the_same_run(client, admin_headers, db_session, monkeypatch):
    """End to end through the real daily job: a product's Rakuten lookup
    times out once, the self-heal pass looks it up again, and the price is
    recorded in the same run - before the analysis stage."""
    monkeypatch.setenv("RAKUTEN_APP_ID", "test-app-id")
    monkeypatch.setenv("RAKUTEN_ACCESS_KEY", "test-access-key")
    from app.config import get_settings
    from app.routers import admin as admin_router

    get_settings.cache_clear()
    product = _product(db_session)

    class _Found:
        price = 58000
        item_name = "PING G430 アイアン"
        item_url = "https://item.rakuten.co.jp/example/g430/"
        image_url = None

    calls = []

    def _search(keyword, **_):
        calls.append(keyword)
        if len(calls) == 1:
            raise TimeoutError("ReadTimeout")
        return _Found()

    monkeypatch.setattr(pipeline.time, "sleep", lambda s: None)
    monkeypatch.setattr(pipeline, "search_lowest_price", _search)
    monkeypatch.setattr(admin_router.popularity, "sync_popularity_rankings", lambda db: (0, 0))
    monkeypatch.setattr(admin_router.discovery, "discover_new_products", lambda db, on_progress=None: (0, 0))
    try:
        resp = client.post("/api/admin/fetch-rakuten", headers=admin_headers)
        assert resp.status_code == 200
        assert len(calls) == 2
        db_session.expire_all()
        assert crud.get_product(db_session, product.id).current_price == 58000
        summary = _summary_rows(db_session)[-1]
        assert "楽天の価格再取得 1/1件成功" in summary.message
    finally:
        get_settings.cache_clear()
