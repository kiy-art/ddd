"""Irons are priced and listed as 5-6本 sets (社長指示 2026-10-10)."""

import httpx
import pytest

from app import crud, iron_sets, models, pipeline, rakuten, schemas


@pytest.mark.parametrize(
    "name, expected",
    [
        ("テーラーメイド Qi アイアンセット 5本組(#6-PW) S", True),
        ("PING G430 アイアン 6本セット", True),
        ("ダンロップ スリクソン Z-FORGED II アイアン 6本組(5-9、PW)", True),
        ("ピン i240 アイアン MODUS3 TOUR125 6I PW(5本セット)", True),
        ("Qi ウィ アイアンセット5本組(#7-PW、SW)", True),
        ("ＰＩＮＧ Ｇ４４０ アイアン ５本セット", True),  # full-width
        ("ピン G440 アイアン 1本 3本 4本 5本 6本 セット 単品アイアン", False),
        ("Miura IC-602 アイアン（単品）", False),
        ("SIM2 MAX アイアンセット 7本 (#5-9,Pw,Aw)", False),
        ("P790 アイアン neo 4本セット", False),
        ("ブリヂストン BSG BG-100 キャディバッグ付き 11本セット アイアンスチール クラブセット", False),
        ("ピンゴルフ カラーコードアイアンカバー (8個セット)", False),
        ("PING G430 アイアン", False),  # no count stated
    ],
)
def test_is_standard_set(name, expected):
    assert iron_sets.is_standard_set(name) is expected


@pytest.mark.parametrize(
    "name, expected",
    [
        ("ピン G440 アイアン 1本 3本 4本 5本 6本 セット", True),
        ("Miura IC-602 アイアン（単品）", True),
        ("TaylorMade P7TW アイアン 3-9P(8本セット)", True),
        ("テーラーメイド セパレート アイアンカバー 8個セット", True),
        ("PING G430 アイアン 6本セット", False),
        ("PING G430 アイアン", False),  # unknown - keep, priced from sets
    ],
)
def test_is_non_standard_listing(name, expected):
    assert iron_sets.is_non_standard_listing(name) is expected


def _rakuten_env(monkeypatch):
    monkeypatch.setenv("RAKUTEN_APP_ID", "test-app-id")
    monkeypatch.setenv("RAKUTEN_ACCESS_KEY", "test-access-key")
    from app.config import get_settings

    get_settings.cache_clear()
    return get_settings


def _item(name, price):
    return {"Item": {"itemName": name, "itemPrice": price, "itemUrl": f"https://item.rakuten.co.jp/x/{price}/"}}


def test_rakuten_iron_search_ignores_single_irons(monkeypatch):
    get_settings = _rakuten_env(monkeypatch)
    payload = {
        "Items": [
            _item("PING G440 アイアン 単品 #5", 29700),
            _item("PING G440 アイアン 1本 3本 4本 5本 6本 セット", 29700),
            _item("PING G440 アイアン 単品 AW", 31900),
            _item("PING G440 アイアン 5本セット", 148500),
            _item("PING G440 アイアン 6本セット(#5-PW)", 178200),
        ]
    }
    monkeypatch.setattr(httpx, "get", lambda url, **kw: httpx.Response(200, json=payload, request=httpx.Request("GET", url)))

    result = rakuten.search_lowest_price("PING G440 アイアン", category="iron")
    assert result is not None
    assert result.price in (148500, 178200)

    # Other categories keep the plain median pick.
    assert rakuten.search_lowest_price("PING G440 アイアン").price == 31900
    get_settings.cache_clear()


def test_rakuten_iron_search_retries_with_set_keyword(monkeypatch):
    get_settings = _rakuten_env(monkeypatch)
    keywords = []

    def fake_get(url, params=None, **kw):
        keywords.append(params["keyword"])
        items = [_item("Miura IC-602 アイアン 単品", 30800)]
        if params["keyword"].endswith("セット"):
            items.append(_item("Miura IC-602 アイアン 6本セット", 184800))
        return httpx.Response(200, json={"Items": items}, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)
    result = rakuten.search_lowest_price("Miura IC-602 アイアン", category="iron")
    assert result.price == 184800
    assert keywords == ["Miura IC-602 アイアン", "Miura IC-602 アイアン セット"]
    get_settings.cache_clear()


class _FakeResult:
    def __init__(self, price, item_name="PING G430 アイアン 5本セット"):
        self.price = price
        self.item_name = item_name
        self.item_url = "https://item.rakuten.co.jp/example/g430/"
        self.image_url = None


def test_pipeline_rebases_single_iron_history_to_set_price(db_session, monkeypatch):
    product = crud.create_product(
        db_session, schemas.ProductCreate(name="IC-602 アイアン", brand="Miura", category="iron", initial_price=30800)
    )
    monkeypatch.setattr(pipeline, "search_lowest_price", lambda keyword, **_: _FakeResult(184800))

    updated, skipped = pipeline.fetch_rakuten_prices(db_session)
    assert (updated, skipped) == (1, 0)
    db_session.refresh(product)
    assert product.current_price == 184800
    assert product.previous_price is None
    assert [h.price for h in crud.get_price_history(db_session, product.id)] == [184800]


def test_pipeline_still_rejects_spike_on_set_priced_iron(db_session, monkeypatch):
    product = crud.create_product(
        db_session, schemas.ProductCreate(name="G430 アイアン", brand="PING", category="iron", initial_price=100000)
    )
    monkeypatch.setattr(pipeline, "search_lowest_price", lambda keyword, **_: _FakeResult(320000))

    assert pipeline.fetch_rakuten_prices(db_session) == (0, 1)
    db_session.refresh(product)
    assert product.current_price == 100000


def test_hide_non_standard_iron_products(db_session):
    def make(name, category="iron"):
        p = crud.create_product(
            db_session, schemas.ProductCreate(name=name, brand="PING", category=category, initial_price=30000)
        )
        p.pending_review = False
        db_session.commit()
        return p

    single = make("G440 アイアン 1本 3本 4本 5本 6本 セット 単品アイアン")
    standard = make("G440 アイアン 5本セット")
    unknown = make("G430 アイアン")
    wedge = make("Glide 4.0 ウェッジ 単品", category="wedge")

    hidden = pipeline.hide_non_standard_iron_products(db_session)
    assert hidden == [single.name]
    for p in (single, standard, unknown, wedge):
        db_session.refresh(p)
    assert single.pending_review is True
    assert not standard.pending_review and not unknown.pending_review and not wedge.pending_review
    assert db_session.get(models.Product, single.id) is not None  # hidden, not deleted
