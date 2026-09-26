import httpx
import pytest

from app import crud, csv_import, image_backfill, image_urls, models, pipeline, rakuten, schemas, yahoo


class _Listing:
    def __init__(self, price=55000, item_name="PING G430 アイアン", image_url="https://thumbnail.image.rakuten.co.jp/@0_mall/shop/g430.jpg"):
        self.price = price
        self.item_name = item_name
        self.item_url = "https://item.rakuten.co.jp/shop/g430/"
        self.image_url = image_url


def _make_product(db, image_url=None, initial_price=60000, name="G430 Iron"):
    product = crud.create_product(
        db, schemas.ProductCreate(name=name, brand="PING", category="iron", initial_price=initial_price)
    )
    # Bypass create_product's normalization to simulate values already
    # stored in production before STEP48 (blank strings, example.com...).
    product.image_url = image_url
    db.commit()
    return product


# --- normalize_image_url / needs_image ------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        (None, None),
        ("", None),
        ("   ", None),
        ("http://thumbnail.image.rakuten.co.jp/a.jpg", "https://thumbnail.image.rakuten.co.jp/a.jpg"),
        ("HTTP://item-shopping.c.yimg.jp/i/l/x.jpg", "https://item-shopping.c.yimg.jp/i/l/x.jpg"),
        ("  https://image.rakuten.co.jp/x.jpg?_ex=128x128 ", "https://image.rakuten.co.jp/x.jpg?_ex=128x128"),
        ("//shop.r10s.jp/a.jpg", "https://shop.r10s.jp/a.jpg"),
        ("https://example.com/nope.jpg", None),  # the sample CSV's placeholder
        ("https://img.example.com/nope.jpg", None),
        ("http://localhost:8765/club.png", None),
        ("images/relative.png", None),
        ("javascript:alert(1)", None),
        ("data:image/png;base64,AAA", None),
        ("ftp://host/a.jpg", None),
    ],
)
def test_normalize_image_url(raw, expected):
    assert image_urls.normalize_image_url(raw) == expected


def test_needs_image_only_for_values_the_site_cannot_show():
    assert image_urls.needs_image(None)
    assert image_urls.needs_image("  ")
    assert image_urls.needs_image("https://example.com/x.jpg")
    assert not image_urls.needs_image("http://thumbnail.image.rakuten.co.jp/a.jpg")  # fixable by upgrading
    assert not image_urls.needs_image("https://www.clubping.jp/a.jpg")


# --- is_definitely_broken ---------------------------------------------------------


class _FakeStream:
    def __init__(self, status, content_type):
        self.status_code = status
        self.headers = {"content-type": content_type}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.mark.parametrize(
    "status, content_type, broken",
    [
        (200, "image/jpeg", False),
        (404, "text/html", True),
        (410, "text/html", True),
        (200, "text/html; charset=utf-8", True),  # an error page served as 200
        (403, "text/html", False),  # may just be a CDN refusing scripts - not proof
        (503, "text/html", False),  # transient outage - never wipe a good photo
    ],
)
def test_is_definitely_broken(monkeypatch, status, content_type, broken):
    monkeypatch.undo()  # drop conftest's always-alive stub for this test
    monkeypatch.setattr(httpx, "stream", lambda *a, **k: _FakeStream(status, content_type))
    assert image_urls.is_definitely_broken("https://thumbnail.image.rakuten.co.jp/a.jpg") is broken


def test_is_definitely_broken_treats_network_errors_as_alive(monkeypatch):
    monkeypatch.undo()

    def _boom(*a, **k):
        raise httpx.ConnectTimeout("timed out")

    monkeypatch.setattr(httpx, "stream", _boom)
    assert image_urls.is_definitely_broken("https://thumbnail.image.rakuten.co.jp/a.jpg") is False


# --- daily price fetch fills photos the site can't show ------------------------------


@pytest.mark.parametrize("stored", [None, "", "   ", "https://example.com/sample.jpg"])
def test_rakuten_fetch_fills_missing_or_placeholder_photo(db_session, monkeypatch, stored):
    product = _make_product(db_session, image_url=stored)
    monkeypatch.setattr(pipeline, "search_lowest_price", lambda keyword: _Listing(image_url="http://thumbnail.image.rakuten.co.jp/@0_mall/shop/g430.jpg"))
    pipeline.fetch_rakuten_prices(db_session)
    db_session.refresh(product)
    assert product.image_url == "https://thumbnail.image.rakuten.co.jp/@0_mall/shop/g430.jpg"


def test_yahoo_fetch_fills_photo_only_when_still_missing(db_session, monkeypatch):
    missing = _make_product(db_session, image_url=None, name="G430 Iron")
    has_photo = _make_product(db_session, image_url="https://thumbnail.image.rakuten.co.jp/keep.jpg", name="G430 Iron B")
    monkeypatch.setattr(pipeline.time, "sleep", lambda s: None)
    monkeypatch.setattr(yahoo, "search_lowest_price", lambda keyword: _Listing(image_url="https://item-shopping.c.yimg.jp/i/l/g430.jpg"))
    pipeline.fetch_yahoo_prices(db_session)
    db_session.refresh(missing)
    db_session.refresh(has_photo)
    assert missing.image_url == "https://item-shopping.c.yimg.jp/i/l/g430.jpg"
    assert has_photo.image_url == "https://thumbnail.image.rakuten.co.jp/keep.jpg"


# --- on-demand backfill -------------------------------------------------------------


@pytest.fixture
def _no_sleep(monkeypatch):
    monkeypatch.setattr(image_backfill.time, "sleep", lambda s: None)


def test_backfill_fills_from_rakuten_without_recording_a_price(db_session, monkeypatch, _no_sleep):
    product = _make_product(db_session, image_url="")
    history_before = len(crud.get_price_history(db_session, product.id))
    monkeypatch.setattr(rakuten, "search_lowest_price", lambda keyword: _Listing())
    monkeypatch.setattr(yahoo, "search_lowest_price", lambda keyword: pytest.fail("Yahoo must not be asked when Rakuten matched"))

    result = image_backfill.backfill_product_images(db_session)

    db_session.refresh(product)
    assert product.image_url == "https://thumbnail.image.rakuten.co.jp/@0_mall/shop/g430.jpg"
    assert result.filled_from_rakuten == 1 and result.still_missing == []
    assert len(crud.get_price_history(db_session, product.id)) == history_before


def test_backfill_falls_back_to_yahoo_and_never_takes_an_accessory_photo(db_session, monkeypatch, _no_sleep):
    product = _make_product(db_session, image_url=None)
    monkeypatch.setattr(rakuten, "search_lowest_price", lambda keyword: _Listing(item_name="PING G430 アイアン用 ヘッドカバー", price=3000))
    monkeypatch.setattr(yahoo, "search_lowest_price", lambda keyword: _Listing(image_url="https://item-shopping.c.yimg.jp/i/l/g430.jpg"))

    result = image_backfill.backfill_product_images(db_session)

    db_session.refresh(product)
    assert product.image_url == "https://item-shopping.c.yimg.jp/i/l/g430.jpg"
    assert result.filled_from_yahoo == 1


def test_backfill_replaces_a_dead_photo_and_keeps_live_ones(db_session, monkeypatch, _no_sleep):
    dead = _make_product(db_session, image_url="https://thumbnail.image.rakuten.co.jp/dead.jpg", name="G430 Iron")
    alive = _make_product(db_session, image_url="https://thumbnail.image.rakuten.co.jp/alive.jpg", name="G430 Iron B")
    monkeypatch.setattr(image_urls, "is_definitely_broken", lambda url, timeout=None: url.endswith("dead.jpg"))
    monkeypatch.setattr(rakuten, "search_lowest_price", lambda keyword: _Listing(image_url="https://thumbnail.image.rakuten.co.jp/new.jpg"))

    result = image_backfill.backfill_product_images(db_session)

    db_session.refresh(dead)
    db_session.refresh(alive)
    assert result.broken_found == 1
    assert dead.image_url == "https://thumbnail.image.rakuten.co.jp/new.jpg"
    assert alive.image_url == "https://thumbnail.image.rakuten.co.jp/alive.jpg"


def test_backfill_reports_what_it_could_not_find_and_clears_the_junk_value(db_session, monkeypatch, _no_sleep):
    product = _make_product(db_session, image_url="https://example.com/sample.jpg", name="Obscure Iron")
    monkeypatch.setattr(rakuten, "search_lowest_price", lambda keyword: None)
    monkeypatch.setattr(yahoo, "search_lowest_price", lambda keyword: None)

    result = image_backfill.backfill_product_images(db_session)

    db_session.refresh(product)
    assert product.image_url is None
    assert result.still_missing == ["Obscure Iron"]


def test_backfill_stops_asking_yahoo_once_the_quota_is_exhausted(db_session, monkeypatch, _no_sleep):
    for i in range(3):
        _make_product(db_session, image_url=None, name=f"Iron {i}")
    calls = []

    def _yahoo(keyword):
        calls.append(keyword)
        raise yahoo.YahooQuotaExceeded("quota")

    monkeypatch.setattr(rakuten, "search_lowest_price", lambda keyword: None)
    monkeypatch.setattr(yahoo, "search_lowest_price", _yahoo)

    result = image_backfill.backfill_product_images(db_session)
    assert len(calls) == 1
    assert result.yahoo_quota_exhausted
    assert len(result.still_missing) == 3


def test_clear_broken_images_clears_dead_and_junk_values_only(db_session, monkeypatch):
    dead = _make_product(db_session, image_url="https://thumbnail.image.rakuten.co.jp/dead.jpg", name="A")
    junk = _make_product(db_session, image_url="  https://example.com/x.jpg ", name="B")
    upgradable = _make_product(db_session, image_url="http://thumbnail.image.rakuten.co.jp/ok.jpg", name="C")
    monkeypatch.setattr(image_urls, "is_definitely_broken", lambda url, timeout=None: url.endswith("dead.jpg"))

    assert image_backfill.clear_broken_images(db_session) == 2

    for p in (dead, junk, upgradable):
        db_session.refresh(p)
    assert dead.image_url is None and junk.image_url is None
    assert upgradable.image_url == "https://thumbnail.image.rakuten.co.jp/ok.jpg"


# --- write paths normalize --------------------------------------------------------


def test_admin_create_and_update_normalize_image_url(db_session):
    product = crud.create_product(
        db_session,
        schemas.ProductCreate(name="X", brand="PING", category="iron", image_url="http://image.rakuten.co.jp/x.jpg"),
    )
    assert product.image_url == "https://image.rakuten.co.jp/x.jpg"
    crud.update_product(db_session, product, schemas.ProductUpdate(image_url="   "))
    assert product.image_url is None


def test_csv_import_normalizes_image_url(db_session):
    content = (
        "product_name,brand,category,model_number,price,product_url,image_url\n"
        "Test Iron,PING,iron,T1,50000,,https://example.com/sample.jpg\n"
        "Test Iron 2,PING,iron,T2,50000,,http://thumbnail.image.rakuten.co.jp/a.jpg\n"
    ).encode()
    csv_import.import_csv(db_session, content)
    by_name = {p.name: p for p in db_session.query(models.Product).all()}
    assert by_name["Test Iron"].image_url is None
    assert by_name["Test Iron 2"].image_url == "https://thumbnail.image.rakuten.co.jp/a.jpg"


# --- admin endpoint ---------------------------------------------------------------


def test_backfill_images_endpoint_requires_admin(client):
    assert client.post("/api/admin/backfill-images").status_code in (401, 403)


def test_backfill_images_endpoint_returns_real_counts(client, admin_headers, db_session, monkeypatch, _no_sleep):
    _make_product(db_session, image_url=None)
    monkeypatch.setattr(rakuten, "search_lowest_price", lambda keyword: _Listing())
    resp = client.post("/api/admin/backfill-images", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["filled_from_rakuten"] == 1
    assert body["still_missing"] == []
