from app import crud, models, x_post


def _make_product(db, **overrides):
    defaults = dict(
        slug=f"test-{overrides.get('name', 'product')}".lower().replace(" ", "-"),
        name="Test Driver",
        brand="TestBrand",
        category="driver",
        msrp=None,
        current_price=50000,
        buy_score="insufficient_data",
        buy_signal_score=None,
        history_span_days=0,
        pending_review=False,
    )
    defaults.update(overrides)
    product = models.Product(**defaults)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def test_select_deals_prefers_reliable_buy_signal(db_session):
    weak = _make_product(
        db_session, name="weak", buy_score="buy", buy_signal_score=60, history_span_days=10
    )
    strong = _make_product(
        db_session, name="strong", buy_score="strong_buy", buy_signal_score=95, history_span_days=10
    )

    picked = x_post.select_deals_of_the_day(db_session, count=2)

    assert [p.id for p in picked] == [strong.id, weak.id]


def test_select_deals_ignores_reliable_scores_from_thin_history(db_session):
    # buy_score is "buy" but history is thin (< RELIABLE_TREND_MIN_HISTORY_DAYS)
    # - must not be trusted as a real signal, matching the frontend's own
    # THIN_DATA_DAYS gate.
    _make_product(db_session, name="thin", buy_score="buy", buy_signal_score=99, history_span_days=1, msrp=None)

    picked = x_post.select_deals_of_the_day(db_session, count=2)

    assert picked == []


def test_select_deals_falls_back_to_msrp_discount(db_session):
    # Neither product has a trustworthy buy_signal_score, but both have a
    # real MSRP discount - the bigger discount should be picked first.
    small_discount = _make_product(
        db_session, name="small", msrp=60000, current_price=57000, buy_score="insufficient_data"
    )
    big_discount = _make_product(
        db_session, name="big", msrp=80000, current_price=52000, buy_score="insufficient_data"
    )

    picked = x_post.select_deals_of_the_day(db_session, count=2)

    assert [p.id for p in picked] == [big_discount.id, small_discount.id]


def test_select_deals_never_features_a_non_discount(db_session):
    # current_price >= msrp - not a deal, must never be featured even as a
    # fallback pick (no fabricating "today's best deal" out of nothing).
    _make_product(db_session, name="no-discount", msrp=50000, current_price=55000)

    picked = x_post.select_deals_of_the_day(db_session, count=2)

    assert picked == []


def test_select_deals_returns_empty_when_nothing_qualifies(db_session):
    _make_product(db_session, name="nothing-to-show", msrp=None, current_price=40000)

    picked = x_post.select_deals_of_the_day(db_session, count=2)

    assert picked == []


def test_select_deals_mixes_reliable_and_fallback_to_fill_count(db_session):
    reliable = _make_product(
        db_session, name="reliable", buy_score="strong_buy", buy_signal_score=90, history_span_days=14
    )
    fallback = _make_product(db_session, name="fallback-only", msrp=70000, current_price=50000)

    picked = x_post.select_deals_of_the_day(db_session, count=2)

    assert {p.id for p in picked} == {reliable.id, fallback.id}


def test_truncate_for_x_keeps_short_text_unchanged():
    body = "短い本文です #ゴルフ"
    assert x_post._truncate_for_x(body) == body


def test_truncate_for_x_shortens_long_text_and_stays_within_budget():
    body = "あ" * 300  # every char weighted 2 - far over budget on its own
    truncated = x_post._truncate_for_x(body)
    budget = x_post.X_MAX_WEIGHTED_LENGTH - 1 - x_post.X_URL_WEIGHTED_LENGTH
    assert x_post._x_weighted_length(truncated) <= budget
    assert truncated.endswith("…")


def test_x_weighted_length_counts_japanese_as_two():
    assert x_post._x_weighted_length("ab") == 2
    assert x_post._x_weighted_length("あい") == 4


def test_post_tweet_raises_when_not_configured(monkeypatch):
    monkeypatch.setenv("X_API_KEY", "")
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        try:
            x_post.post_tweet("hello")
            assert False, "expected XNotConfigured"
        except x_post.XNotConfigured:
            pass
    finally:
        get_settings.cache_clear()


def test_oauth1_authorization_header_shape(monkeypatch):
    monkeypatch.setenv("X_API_KEY", "consumer-key")
    monkeypatch.setenv("X_API_SECRET", "consumer-secret")
    monkeypatch.setenv("X_ACCESS_TOKEN", "access-token")
    monkeypatch.setenv("X_ACCESS_TOKEN_SECRET", "access-token-secret")
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        header = x_post._oauth1_authorization_header("POST", x_post.POST_URL)
        assert header.startswith("OAuth ")
        for key in (
            "oauth_consumer_key",
            "oauth_nonce",
            "oauth_signature",
            "oauth_signature_method",
            "oauth_timestamp",
            "oauth_token",
            "oauth_version",
        ):
            assert key in header
        assert 'oauth_signature_method="HMAC-SHA1"' in header
    finally:
        get_settings.cache_clear()


def test_post_daily_deals_noop_when_not_configured(db_session, monkeypatch):
    monkeypatch.setenv("X_API_KEY", "")
    from app.config import get_settings

    get_settings.cache_clear()
    _make_product(db_session, name="strong", buy_score="strong_buy", buy_signal_score=95, history_span_days=14)
    try:
        sent, skipped = x_post.post_daily_deals(db_session)
        assert (sent, skipped) == (0, 0)
    finally:
        get_settings.cache_clear()


def test_post_daily_deals_noop_when_nothing_to_feature(db_session, monkeypatch):
    monkeypatch.setenv("X_API_KEY", "k")
    monkeypatch.setenv("X_API_SECRET", "s")
    monkeypatch.setenv("X_ACCESS_TOKEN", "t")
    monkeypatch.setenv("X_ACCESS_TOKEN_SECRET", "ts")
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        sent, skipped = x_post.post_daily_deals(db_session)
        assert (sent, skipped) == (0, 0)
    finally:
        get_settings.cache_clear()


def test_post_daily_deals_success_logs_info(db_session, monkeypatch):
    monkeypatch.setenv("X_API_KEY", "k")
    monkeypatch.setenv("X_API_SECRET", "s")
    monkeypatch.setenv("X_ACCESS_TOKEN", "t")
    monkeypatch.setenv("X_ACCESS_TOKEN_SECRET", "ts")
    from app.config import get_settings

    get_settings.cache_clear()
    _make_product(db_session, name="strong", buy_score="strong_buy", buy_signal_score=95, history_span_days=14, msrp=60000, current_price=45000)
    monkeypatch.setattr(x_post, "post_tweet", lambda text, timeout=10.0: "1234567890")

    try:
        sent, skipped = x_post.post_daily_deals(db_session)
        assert (sent, skipped) == (1, 0)
        logs = crud.list_error_logs(db_session)
        assert any(log.source == "x_post" and log.level == "info" and "1234567890" in log.message for log in logs)
    finally:
        get_settings.cache_clear()


def test_build_manual_post_text_matches_what_post_daily_deals_would_tweet(db_session, monkeypatch):
    monkeypatch.setenv("X_API_KEY", "k")
    monkeypatch.setenv("X_API_SECRET", "s")
    monkeypatch.setenv("X_ACCESS_TOKEN", "t")
    monkeypatch.setenv("X_ACCESS_TOKEN_SECRET", "ts")
    from app.config import get_settings

    get_settings.cache_clear()
    _make_product(
        db_session, name="strong", buy_score="strong_buy", buy_signal_score=95, history_span_days=14, msrp=60000, current_price=45000
    )
    captured = {}
    monkeypatch.setattr(x_post, "post_tweet", lambda text, timeout=10.0: captured.setdefault("text", text) or "1")

    try:
        preview_text = x_post.build_manual_post_text(db_session)
        assert preview_text is not None
        x_post.post_daily_deals(db_session)
        assert preview_text == captured["text"]
    finally:
        get_settings.cache_clear()


def test_build_manual_post_text_returns_none_when_nothing_qualifies(db_session):
    _make_product(db_session, name="nothing-to-show", msrp=None, current_price=40000)
    assert x_post.build_manual_post_text(db_session) is None


def test_post_daily_deals_gracefully_skips_on_402_without_treating_it_as_an_error(db_session, monkeypatch):
    """X's free API tier stopped allowing tweet creation (402 Payment
    Required) - a standing condition, not a transient failure, so this
    must be a graceful skip (info-level log carrying the ready-to-paste
    text) rather than an alarming error, per the new manual-posting
    workflow."""
    monkeypatch.setenv("X_API_KEY", "k")
    monkeypatch.setenv("X_API_SECRET", "s")
    monkeypatch.setenv("X_ACCESS_TOKEN", "t")
    monkeypatch.setenv("X_ACCESS_TOKEN_SECRET", "ts")
    from app.config import get_settings

    get_settings.cache_clear()
    _make_product(
        db_session, name="strong", buy_score="strong_buy", buy_signal_score=95, history_span_days=14, msrp=60000, current_price=45000
    )

    def _payment_required(text, timeout=10.0):
        raise x_post.XPostError("X API 402: payment required", status_code=402)

    monkeypatch.setattr(x_post, "post_tweet", _payment_required)

    try:
        sent, skipped = x_post.post_daily_deals(db_session)
        assert (sent, skipped) == (0, 1)
        logs = crud.list_error_logs(db_session)
        assert not any(log.source == "x_post" and log.level == "error" for log in logs)
        assert any(
            log.source == "x_post" and log.level == "info" and "402" in log.message and "手動投稿用テキスト" in log.message
            for log in logs
        )
    finally:
        get_settings.cache_clear()


def test_x_post_preview_endpoint_requires_admin_auth(client):
    resp = client.get("/api/admin/x-post-preview")
    assert resp.status_code in (401, 403)


def test_x_post_preview_endpoint_returns_null_when_nothing_qualifies(client, admin_headers, db_session):
    _make_product(db_session, name="nothing-to-show", msrp=None, current_price=40000)
    resp = client.get("/api/admin/x-post-preview", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json() == {"text": None}


def test_x_post_preview_endpoint_returns_the_ready_to_paste_text(client, admin_headers, db_session):
    _make_product(
        db_session, name="strong", buy_score="strong_buy", buy_signal_score=95, history_span_days=14, msrp=60000, current_price=45000
    )
    resp = client.get("/api/admin/x-post-preview", headers=admin_headers)
    assert resp.status_code == 200
    text = resp.json()["text"]
    assert text is not None
    assert "#ゴルフ" in text
    # No X credentials configured in the test environment - the preview
    # must not depend on them, since it's read-only and never posts.


def test_post_daily_deals_failure_logs_error_and_does_not_raise(db_session, monkeypatch):
    monkeypatch.setenv("X_API_KEY", "k")
    monkeypatch.setenv("X_API_SECRET", "s")
    monkeypatch.setenv("X_ACCESS_TOKEN", "t")
    monkeypatch.setenv("X_ACCESS_TOKEN_SECRET", "ts")
    from app.config import get_settings

    get_settings.cache_clear()
    _make_product(db_session, name="strong", buy_score="strong_buy", buy_signal_score=95, history_span_days=14, msrp=60000, current_price=45000)

    def _boom(text, timeout=10.0):
        raise x_post.XPostError("X API 503: temporarily unavailable")

    monkeypatch.setattr(x_post, "post_tweet", _boom)

    try:
        sent, skipped = x_post.post_daily_deals(db_session)
        assert (sent, skipped) == (0, 1)
        logs = crud.list_error_logs(db_session)
        assert any(log.source == "x_post" and log.level == "error" for log in logs)
    finally:
        get_settings.cache_clear()
