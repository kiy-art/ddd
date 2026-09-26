from app import crud, email, pipeline, schemas, yahoo


def _make_product(db, initial_price=60000):
    return crud.create_product(
        db,
        schemas.ProductCreate(name="G430 Iron", brand="PING", category="iron", initial_price=initial_price),
    )


class _FakeResult:
    def __init__(
        self,
        price,
        item_name="PING G430 アイアン",
        item_url="https://item.rakuten.co.jp/example/g430/",
        image_url=None,
    ):
        self.price = price
        self.item_name = item_name
        self.item_url = item_url
        self.image_url = image_url


def test_fetch_rakuten_prices_rejects_implausible_drop(db_session, monkeypatch):
    """A search match wildly below the known average (e.g. a mismatched
    accessory/part) must be logged and skipped, never applied as the real
    price — this is the guard added after the PING G430 ¥1,100 incident."""
    product = _make_product(db_session, initial_price=60000)

    monkeypatch.setattr(pipeline, "search_lowest_price", lambda keyword: _FakeResult(1100))

    updated, skipped = pipeline.fetch_rakuten_prices(db_session)
    assert updated == 0
    assert skipped == 1

    db_session.refresh(product)
    assert product.current_price == 60000

    logs = crud.list_error_logs(db_session)
    assert any("乖離" in log.message and log.level == "warning" for log in logs)


def test_fetch_rakuten_prices_rejects_implausible_spike(db_session, monkeypatch):
    product = _make_product(db_session, initial_price=60000)

    monkeypatch.setattr(pipeline, "search_lowest_price", lambda keyword: _FakeResult(200000))

    updated, skipped = pipeline.fetch_rakuten_prices(db_session)
    assert updated == 0
    assert skipped == 1

    db_session.refresh(product)
    assert product.current_price == 60000


def test_fetch_rakuten_prices_accepts_plausible_price(db_session, monkeypatch):
    product = _make_product(db_session, initial_price=60000)

    monkeypatch.setattr(pipeline, "search_lowest_price", lambda keyword: _FakeResult(55000))

    updated, skipped = pipeline.fetch_rakuten_prices(db_session)
    assert updated == 1
    assert skipped == 0

    db_session.refresh(product)
    assert product.current_price == 55000


def test_fetch_rakuten_prices_fills_in_blank_image_and_affiliate_url(db_session, monkeypatch):
    product = _make_product(db_session, initial_price=60000)
    assert product.image_url is None
    assert product.affiliate_url is None

    monkeypatch.setattr(
        pipeline,
        "search_lowest_price",
        lambda keyword: _FakeResult(
            55000,
            item_url="https://item.rakuten.co.jp/example/g430/",
            image_url="https://thumbnail.image.rakuten.co.jp/example/g430.jpg",
        ),
    )

    pipeline.fetch_rakuten_prices(db_session)

    db_session.refresh(product)
    assert product.image_url == "https://thumbnail.image.rakuten.co.jp/example/g430.jpg"
    assert product.affiliate_url == "https://item.rakuten.co.jp/example/g430/"


def test_fetch_rakuten_prices_never_overwrites_existing_image_or_affiliate_url(db_session, monkeypatch):
    product = _make_product(db_session, initial_price=60000)
    # A real, valid photo an admin chose (example.com would count as a
    # placeholder the site can't show - see image_urls.PLACEHOLDER_HOSTS).
    product.image_url = "https://www.clubping.jp/images/manually-curated.jpg"
    product.affiliate_url = "https://example.com/manually-curated-link"
    db_session.commit()

    monkeypatch.setattr(
        pipeline,
        "search_lowest_price",
        lambda keyword: _FakeResult(
            55000,
            item_url="https://item.rakuten.co.jp/example/g430/",
            image_url="https://thumbnail.image.rakuten.co.jp/example/g430.jpg",
        ),
    )

    pipeline.fetch_rakuten_prices(db_session)

    db_session.refresh(product)
    assert product.image_url == "https://www.clubping.jp/images/manually-curated.jpg"
    assert product.affiliate_url == "https://example.com/manually-curated-link"


def test_fetch_rakuten_prices_wraps_affiliate_url_when_affiliate_id_configured(db_session, monkeypatch):
    monkeypatch.setenv("RAKUTEN_AFFILIATE_ID", "38e4bda3.3d4c8086.38e4bda4.cefadc6a")
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        product = _make_product(db_session, initial_price=60000)

        monkeypatch.setattr(
            pipeline,
            "search_lowest_price",
            lambda keyword: _FakeResult(55000, item_url="https://item.rakuten.co.jp/example/g430/"),
        )

        pipeline.fetch_rakuten_prices(db_session)

        db_session.refresh(product)
        assert product.affiliate_url.startswith(
            "https://hb.afl.rakuten.co.jp/ichiba/38e4bda3.3d4c8086.38e4bda4.cefadc6a/?pc="
        )
    finally:
        get_settings.cache_clear()


def test_fetch_rakuten_prices_accepts_any_price_with_no_history_reference(db_session, monkeypatch):
    """A brand-new product with only an initial price still has an average
    set from that single point, so this really exercises the case where a
    product has no plausible reference at all (average/current both None)."""
    product = crud.create_product(
        db_session, schemas.ProductCreate(name="New Ball", brand="Titleist", category="ball")
    )
    assert product.average_price is None
    assert product.current_price is None

    monkeypatch.setattr(pipeline, "search_lowest_price", lambda keyword: _FakeResult(500))

    updated, skipped = pipeline.fetch_rakuten_prices(db_session)
    assert updated == 1
    assert skipped == 0


def test_fetch_rakuten_prices_rejects_accessory_match_even_with_no_reference(db_session, monkeypatch):
    """The gap behind the real incident: a brand-new product has no
    reference price yet, so _is_plausible_price alone would accept anything
    — including a cheap accessory/part listing matched instead of the real
    product (an ELYTE MAX FAST driver's first fetch briefly became a
    ¥2,180 sole-weight-port cap). The accessory-keyword check must catch
    this independently of price plausibility."""
    product = crud.create_product(
        db_session, schemas.ProductCreate(name="ELYTE MAX FAST ドライバー", brand="Callaway", category="driver")
    )
    assert product.current_price is None

    monkeypatch.setattr(
        pipeline,
        "search_lowest_price",
        lambda keyword: _FakeResult(2180, item_name="キャロウェイ ELYTE MAX FAST用 ソールウェイト"),
    )

    updated, skipped = pipeline.fetch_rakuten_prices(db_session)
    assert updated == 0
    assert skipped == 1

    db_session.refresh(product)
    assert product.current_price is None
    assert product.image_url is None

    logs = crud.list_error_logs(db_session)
    assert any("アクセサリ" in log.message and log.level == "warning" for log in logs)


def test_fetch_rakuten_prices_rejects_non_retail_listing_match(db_session, monkeypatch):
    """A furusato-nozei donation-reward listing (or a damaged/defective
    clearance listing) matched by keyword search isn't a real retail price
    for the product and must be rejected the same way an accessory match
    is (STEP15)."""
    product = _make_product(db_session, initial_price=60000)

    monkeypatch.setattr(
        pipeline,
        "search_lowest_price",
        lambda keyword: _FakeResult(55000, item_name="PING G430 ドライバー ふるさと納税"),
    )

    updated, skipped = pipeline.fetch_rakuten_prices(db_session)
    assert updated == 0
    assert skipped == 1

    db_session.refresh(product)
    assert product.current_price == 60000  # unchanged


def test_fetch_yahoo_prices_accepts_plausible_price(db_session, monkeypatch):
    product = _make_product(db_session, initial_price=60000)

    monkeypatch.setattr(
        yahoo, "search_lowest_price", lambda keyword: _FakeResult(58000, item_url="https://store.shopping.yahoo.co.jp/example/g430.html")
    )

    updated, skipped = pipeline.fetch_yahoo_prices(db_session)
    assert updated == 1
    assert skipped == 0

    db_session.refresh(product)
    assert product.yahoo_price == 58000
    assert product.yahoo_url == "https://store.shopping.yahoo.co.jp/example/g430.html"
    assert product.yahoo_updated_at is not None


def test_fetch_yahoo_prices_stops_early_on_quota_exceeded(db_session, monkeypatch):
    """A real production incident: Yahoo's daily call quota being exhausted
    mid-run used to produce one near-identical ErrorLog row per remaining
    product (~25 in one real run) since each lookup failed independently.
    Once YahooQuotaExceeded is raised, the whole run should stop immediately
    with a single summary log instead of retrying it for every product."""
    for i in range(3):
        crud.create_product(
            db_session,
            schemas.ProductCreate(name=f"Product {i}", brand="PING", category="iron", initial_price=60000),
        )

    calls = []

    def fake_search(keyword):
        calls.append(keyword)
        raise yahoo.YahooQuotaExceeded("Yahoo Shopping API 429: quota exhausted")

    monkeypatch.setattr(yahoo, "search_lowest_price", fake_search)

    updated, skipped = pipeline.fetch_yahoo_prices(db_session)
    assert updated == 0
    assert skipped == 3
    assert len(calls) == 1  # stopped after the first quota-exhaustion hit

    error_logs = crud.list_error_logs(db_session)
    quota_logs = [log for log in error_logs if "quota exhausted" in log.message]
    assert len(quota_logs) == 1


def test_fetch_yahoo_prices_rejects_implausible_price(db_session, monkeypatch):
    product = _make_product(db_session, initial_price=60000)

    monkeypatch.setattr(yahoo, "search_lowest_price", lambda keyword: _FakeResult(1100))

    updated, skipped = pipeline.fetch_yahoo_prices(db_session)
    assert updated == 0
    assert skipped == 1

    db_session.refresh(product)
    assert product.yahoo_price is None


def test_fetch_yahoo_prices_rejects_accessory_match(db_session, monkeypatch):
    product = _make_product(db_session, initial_price=60000)

    monkeypatch.setattr(
        yahoo, "search_lowest_price", lambda keyword: _FakeResult(58000, item_name="PING G430用 ヘッドカバー")
    )

    updated, skipped = pipeline.fetch_yahoo_prices(db_session)
    assert updated == 0
    assert skipped == 1

    db_session.refresh(product)
    assert product.yahoo_price is None


def test_fetch_yahoo_prices_rejects_non_retail_listing_match(db_session, monkeypatch):
    product = _make_product(db_session, initial_price=60000)

    monkeypatch.setattr(
        yahoo, "search_lowest_price", lambda keyword: _FakeResult(58000, item_name="PING G430 ドライバー 訳あり")
    )

    updated, skipped = pipeline.fetch_yahoo_prices(db_session)
    assert updated == 0
    assert skipped == 1

    db_session.refresh(product)
    assert product.yahoo_price is None


def test_fetch_yahoo_prices_clears_stale_price_when_no_longer_matched(db_session, monkeypatch):
    """A product that had a Yahoo price on a previous fetch but no longer
    matches (delisted, price no longer plausible) must have it cleared, not
    left showing an old price as if it were current."""
    product = _make_product(db_session, initial_price=60000)
    product.yahoo_price = 59000
    product.yahoo_url = "https://store.shopping.yahoo.co.jp/example/old.html"
    db_session.commit()

    monkeypatch.setattr(yahoo, "search_lowest_price", lambda keyword: None)

    updated, skipped = pipeline.fetch_yahoo_prices(db_session)
    assert updated == 0
    assert skipped == 1

    db_session.refresh(product)
    assert product.yahoo_price is None
    assert product.yahoo_url is None


def test_fetch_yahoo_prices_never_touches_rakuten_sourced_fields(db_session, monkeypatch):
    """Yahoo is a second, independent price source - it must never disturb
    current_price/buy_score/price_history, which stay anchored to the
    Rakuten-sourced series."""
    product = _make_product(db_session, initial_price=60000)
    original_buy_score = product.buy_score
    original_current_price = product.current_price
    history_before = len(crud.get_price_history(db_session, product.id))

    monkeypatch.setattr(yahoo, "search_lowest_price", lambda keyword: _FakeResult(55000))

    pipeline.fetch_yahoo_prices(db_session)

    db_session.refresh(product)
    assert product.current_price == original_current_price
    assert product.buy_score == original_buy_score
    assert len(crud.get_price_history(db_session, product.id)) == history_before


def test_fetch_yahoo_prices_wraps_affiliate_url_when_configured(db_session, monkeypatch):
    monkeypatch.setenv("YAHOO_AFFILIATE_ID", "test-sid-123")
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        product = _make_product(db_session, initial_price=60000)

        monkeypatch.setattr(
            yahoo,
            "search_lowest_price",
            lambda keyword: _FakeResult(55000, item_url="https://store.shopping.yahoo.co.jp/example/g430.html"),
        )

        pipeline.fetch_yahoo_prices(db_session)

        db_session.refresh(product)
        assert product.yahoo_url.startswith("https://ck.jp.ap.valuecommerce.com/servlet/referral?sid=test-sid-123")
    finally:
        get_settings.cache_clear()


def test_send_price_alert_notifications_is_noop_when_not_configured(db_session, monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "")
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        product = _make_product(db_session, initial_price=90000)
        crud.create_price_alert(db_session, product, schemas.PriceAlertCreate(email="user@example.com", target_price=100000))

        sent_calls = []
        monkeypatch.setattr(email, "send_email", lambda **kwargs: sent_calls.append(kwargs))

        sent, skipped = pipeline.send_price_alert_notifications(db_session)
        assert (sent, skipped) == (0, 0)
        assert sent_calls == []
    finally:
        get_settings.cache_clear()


def test_send_price_alert_notifications_sends_when_target_reached(db_session, monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "test-key")
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        product = _make_product(db_session, initial_price=90000)  # already below the target
        alert = crud.create_price_alert(
            db_session, product, schemas.PriceAlertCreate(email="user@example.com", target_price=100000)
        )

        sent_calls = []
        monkeypatch.setattr(email, "send_email", lambda **kwargs: sent_calls.append(kwargs))

        sent, skipped = pipeline.send_price_alert_notifications(db_session)
        assert (sent, skipped) == (1, 0)
        assert len(sent_calls) == 1
        assert sent_calls[0]["to"] == "user@example.com"

        db_session.refresh(alert)
        assert alert.notified_at is not None
    finally:
        get_settings.cache_clear()


def test_send_price_alert_notifications_skips_when_target_not_yet_reached(db_session, monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "test-key")
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        product = _make_product(db_session, initial_price=120000)  # still above the target
        alert = crud.create_price_alert(
            db_session, product, schemas.PriceAlertCreate(email="user@example.com", target_price=100000)
        )

        sent_calls = []
        monkeypatch.setattr(email, "send_email", lambda **kwargs: sent_calls.append(kwargs))

        sent, skipped = pipeline.send_price_alert_notifications(db_session)
        assert (sent, skipped) == (0, 0)
        assert sent_calls == []

        db_session.refresh(alert)
        assert alert.notified_at is None
    finally:
        get_settings.cache_clear()


def test_send_price_alert_notifications_never_resends_an_already_notified_alert(db_session, monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "test-key")
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        product = _make_product(db_session, initial_price=90000)
        alert = crud.create_price_alert(
            db_session, product, schemas.PriceAlertCreate(email="user@example.com", target_price=100000)
        )
        crud.mark_price_alert_notified(db_session, alert)

        sent_calls = []
        monkeypatch.setattr(email, "send_email", lambda **kwargs: sent_calls.append(kwargs))

        sent, skipped = pipeline.send_price_alert_notifications(db_session)
        assert (sent, skipped) == (0, 0)
        assert sent_calls == []
    finally:
        get_settings.cache_clear()


def test_send_price_alert_notifications_leaves_alert_unmarked_on_send_failure(db_session, monkeypatch):
    """A Resend failure must not silently lose the alert - it stays
    untriggered so the next run retries it."""
    monkeypatch.setenv("RESEND_API_KEY", "test-key")
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        product = _make_product(db_session, initial_price=90000)
        alert = crud.create_price_alert(
            db_session, product, schemas.PriceAlertCreate(email="user@example.com", target_price=100000)
        )

        def failing_send(**kwargs):
            raise email.EmailSendError("Resend API 500: boom")

        monkeypatch.setattr(email, "send_email", failing_send)

        sent, skipped = pipeline.send_price_alert_notifications(db_session)
        assert (sent, skipped) == (0, 1)

        db_session.refresh(alert)
        assert alert.notified_at is None

        logs = crud.list_error_logs(db_session)
        assert any("price_alert_email" == log.source for log in logs)
    finally:
        get_settings.cache_clear()


def test_find_and_fix_price_anomalies_cleans_up_preexisting_bad_row(db_session):
    """Simulates data corrupted before the sanity-check guard existed: a
    product with legitimate prices plus one bad ¥1,100 row already written
    to history. The scan must flag it and the fix must remove it and
    recompute the product's stats."""
    product = _make_product(db_session, initial_price=60000)
    crud.add_price(db_session, product, 59000)
    crud.add_price(db_session, product, 1100)

    # A healthy, untouched product must never be flagged.
    healthy = crud.create_product(
        db_session,
        schemas.ProductCreate(name="G440 Driver", brand="PING", category="driver", initial_price=70000),
    )
    crud.add_price(db_session, healthy, 68000)

    anomalies = pipeline.find_price_anomalies(db_session)
    assert len(anomalies) == 1
    assert anomalies[0]["product_id"] == product.id
    assert anomalies[0]["price"] == 1100

    fixed = pipeline.fix_price_anomalies(db_session)
    assert len(fixed) == 1

    db_session.refresh(product)
    assert product.current_price == 59000
    assert product.lowest_price == 59000

    remaining_prices = [h.price for h in crud.get_price_history(db_session, product.id)]
    assert 1100 not in remaining_prices

    assert pipeline.find_price_anomalies(db_session) == []


# --- STEP43: routine regeneration must not erase an optimizer rewrite -------


def _optimized_product(db):
    import datetime
    import json

    from app import models

    product = _make_product(db)
    for days_ago, price in ((20, 60000), (10, 60000)):
        row = crud.add_price(db, product, price)
        row.recorded_at = datetime.datetime.utcnow() - datetime.timedelta(days=days_ago)
    db.commit()
    action = models.AiOptimizationAction(
        action_type="rewrite_product",
        target_path=f"/products/{product.slug}",
        product_id=product.id,
        decision_basis="検索クリック率がサイト平均未満",
        content_after=json.dumps({"ai_title": "最適化タイトル", "goal": "search_ctr", "queries": [{"query": "g430"}]}),
        status="applied",
    )
    db.add(action)
    db.flush()
    product.ai_title = "最適化タイトル"
    product.ai_copy_source_action_id = action.id
    product.ai_content_hash = "stale-facts"
    db.commit()
    return product, action


def test_price_change_regenerates_in_the_optimizers_style_not_routine_copy(db_session, monkeypatch):
    from app import ai, content_rewriter

    product, action = _optimized_product(db_session)
    monkeypatch.setattr(ai, "would_use_claude", lambda result: True)
    calls = []

    def _rewrite(product, reason, goal=None, search_queries=None):
        calls.append((goal, search_queries))
        return content_rewriter.RewrittenProductCopy(title="最適化タイトル（新価格）", summary="s", caution="c")

    monkeypatch.setattr(content_rewriter, "rewrite_product_copy", _rewrite)
    monkeypatch.setattr(ai, "generate_ai_content_safe", lambda *a, **k: (_ for _ in ()).throw(AssertionError("routine copy used")))

    assert pipeline.sync_product_analysis(db_session, product) is True
    db_session.refresh(product)
    assert calls == [("search_ctr", [{"query": "g430"}])]
    assert product.ai_title == "最適化タイトル（新価格）"
    assert product.ai_copy_source_action_id == action.id


def test_optimized_style_never_adds_a_claude_call_the_routine_path_wouldnt_make(db_session, monkeypatch):
    from app import ai, content_rewriter

    product, _ = _optimized_product(db_session)
    monkeypatch.setattr(ai, "would_use_claude", lambda result: False)
    monkeypatch.setattr(
        content_rewriter, "rewrite_product_copy", lambda *a, **k: (_ for _ in ()).throw(AssertionError("extra Claude call"))
    )

    pipeline.sync_product_analysis(db_session, product)
    db_session.refresh(product)
    # Routine (free, rule-based) copy took over, so the marker is cleared -
    # evaluate_past_actions will report the old decision as inconclusive.
    assert product.ai_copy_source_action_id is None
