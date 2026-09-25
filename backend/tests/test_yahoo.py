import httpx
import pytest

from app import yahoo


def test_raises_when_client_id_missing(monkeypatch):
    monkeypatch.setenv("YAHOO_CLIENT_ID", "")
    from app.config import get_settings

    get_settings.cache_clear()
    with pytest.raises(yahoo.YahooNotConfigured):
        yahoo.search_lowest_price("PING G440")
    get_settings.cache_clear()


def test_search_lowest_price_returns_first_result(monkeypatch):
    monkeypatch.setenv("YAHOO_CLIENT_ID", "test-client-id")
    from app.config import get_settings

    get_settings.cache_clear()

    payload = {
        "hits": [
            {
                "name": "PING G440 ドライバー",
                "price": 68000,
                "url": "https://store.shopping.yahoo.co.jp/example/g440.html",
                "image": {"medium": "https://item-shopping.c.yimg.jp/example/g440.jpg"},
            }
        ]
    }

    def fake_get(url, params=None, timeout=None):
        assert params["appid"] == "test-client-id"
        assert params["query"] == "PING G440"
        return httpx.Response(200, json=payload, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)

    result = yahoo.search_lowest_price("PING G440")
    assert result is not None
    assert result.price == 68000
    assert result.item_url == "https://store.shopping.yahoo.co.jp/example/g440.html"
    assert result.image_url == "https://item-shopping.c.yimg.jp/example/g440.jpg"

    get_settings.cache_clear()


def test_search_lowest_price_picks_median_over_outlier(monkeypatch):
    """Same mismatch-resistant selection as Rakuten's client - a junk/
    irrelevant cheap listing must not be picked just because it's the
    lowest price among the results."""
    monkeypatch.setenv("YAHOO_CLIENT_ID", "test-client-id")
    from app.config import get_settings

    get_settings.cache_clear()

    def make_hit(name, price, path):
        return {
            "name": name,
            "price": price,
            "url": f"https://store.shopping.yahoo.co.jp/example/{path}.html",
            "image": {},
        }

    payload = {
        "hits": [
            make_hit("PING G430 用 交換パーツ", 1100, "junk"),
            make_hit("PING G430 アイアン セット", 58000, "a"),
            make_hit("PING G430 アイアン", 60000, "b"),
            make_hit("PING G430 アイアン 中古美品", 62000, "c"),
        ]
    }

    def fake_get(url, params=None, timeout=None):
        assert "sort" not in params
        return httpx.Response(200, json=payload, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)

    result = yahoo.search_lowest_price("PING G430")
    assert result is not None
    assert result.price == 60000
    get_settings.cache_clear()


def test_search_lowest_price_returns_none_when_no_hits(monkeypatch):
    monkeypatch.setenv("YAHOO_CLIENT_ID", "test-client-id")
    from app.config import get_settings

    get_settings.cache_clear()

    def fake_get(url, params=None, timeout=None):
        return httpx.Response(200, json={"hits": []}, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)

    assert yahoo.search_lowest_price("nonexistent item xyz") is None
    get_settings.cache_clear()


def test_search_lowest_price_skips_hits_missing_required_fields(monkeypatch):
    """Same defensive filter as rakuten.py: a hit missing price/url/name
    must not crash the lookup with a bare KeyError."""
    monkeypatch.setenv("YAHOO_CLIENT_ID", "test-client-id")
    from app.config import get_settings

    get_settings.cache_clear()

    payload = {
        "hits": [
            {"name": "価格未定の商品"},  # missing price/url
            {
                "name": "PING G440 ドライバー",
                "price": 68000,
                "url": "https://store.shopping.yahoo.co.jp/example/g440.html",
                "image": {"medium": "https://item-shopping.c.yimg.jp/example/g440.jpg"},
            },
        ]
    }

    def fake_get(url, params=None, timeout=None):
        return httpx.Response(200, json=payload, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)

    result = yahoo.search_lowest_price("PING G440")
    assert result is not None
    assert result.price == 68000
    get_settings.cache_clear()


def test_to_affiliate_url_returns_none_when_not_configured(monkeypatch):
    monkeypatch.setenv("YAHOO_AFFILIATE_ID", "")
    from app.config import get_settings

    get_settings.cache_clear()
    assert yahoo.to_affiliate_url("https://store.shopping.yahoo.co.jp/example/g440.html") is None
    get_settings.cache_clear()


def test_to_affiliate_url_wraps_the_item_url_with_the_configured_id(monkeypatch):
    monkeypatch.setenv("YAHOO_AFFILIATE_ID", "test-sid-123")
    from app.config import get_settings

    get_settings.cache_clear()

    result = yahoo.to_affiliate_url("https://store.shopping.yahoo.co.jp/example/g440.html")
    assert result is not None
    assert result.startswith("https://ck.jp.ap.valuecommerce.com/servlet/referral?sid=test-sid-123")
    assert "store.shopping.yahoo.co.jp%2Fexample%2Fg440.html" in result

    get_settings.cache_clear()
