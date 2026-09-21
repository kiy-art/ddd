from app import crud, pipeline, schemas


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
    product.image_url = "https://example.com/manually-curated.jpg"
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
    assert product.image_url == "https://example.com/manually-curated.jpg"
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
