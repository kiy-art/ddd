from app import crud, pipeline, schemas


def _make_product(db, initial_price=60000):
    return crud.create_product(
        db,
        schemas.ProductCreate(name="G430 Iron", brand="PING", category="iron", initial_price=initial_price),
    )


class _FakeResult:
    def __init__(self, price, item_name="PING G430 アイアン", item_url="https://item.rakuten.co.jp/example/g430/"):
        self.price = price
        self.item_name = item_name
        self.item_url = item_url
        self.image_url = None


def test_fetch_rakuten_prices_rejects_implausible_drop(db_session, monkeypatch):
    """A search match wildly below the known average (e.g. a mismatched
    accessory/part) must be logged and skipped, never applied as the real
    price — this is the guard added after the PING G430 ¥1,100 incident."""
    product = _make_product(db_session, initial_price=60000)

    monkeypatch.setattr(
        pipeline, "search_lowest_price", lambda keyword: _FakeResult(1100, item_name="PING G430 用 交換パーツ")
    )

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
