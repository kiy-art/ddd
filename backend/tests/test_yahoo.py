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


def test_search_lowest_price_raises_quota_exceeded_on_429_appid_denied(monkeypatch):
    """A real production error: 'total count of AppID reached the URL's
    limit count' is a daily-quota exhaustion, not a transient rate limit -
    it must surface as YahooQuotaExceeded (a RuntimeError subclass callers
    can special-case) rather than the generic RuntimeError, and must not be
    retried since every retry would fail identically."""
    monkeypatch.setenv("YAHOO_CLIENT_ID", "test-client-id")
    from app.config import get_settings

    get_settings.cache_clear()

    calls = []
    body = '{ "Status": 429, "Message":"The AppID is denied: total count of AppID reached the URL\'s limit count." }'

    def fake_get(url, params=None, timeout=None):
        calls.append(1)
        return httpx.Response(429, text=body, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)

    with pytest.raises(yahoo.YahooQuotaExceeded):
        yahoo.search_lowest_price("PING G440")
    assert len(calls) == 1  # not retried - it's a permanent condition this run

    get_settings.cache_clear()


def test_to_affiliate_url_returns_none_when_not_configured(monkeypatch):
    monkeypatch.setenv("YAHOO_AFFILIATE_ID", "")
    from app.config import get_settings

    get_settings.cache_clear()
    assert yahoo.to_affiliate_url("https://store.shopping.yahoo.co.jp/example/g440.html") is None
    get_settings.cache_clear()


def test_to_affiliate_url_needs_both_sid_and_pid(monkeypatch):
    # STEP67: a MyLink with an empty pid isn't credited by ValueCommerce.
    monkeypatch.setenv("YAHOO_AFFILIATE_ID", "3123456")
    monkeypatch.setenv("YAHOO_AFFILIATE_PID", "")
    from app.config import get_settings

    get_settings.cache_clear()
    assert yahoo.to_affiliate_url("https://store.shopping.yahoo.co.jp/example/g440.html") is None
    get_settings.cache_clear()


def test_to_affiliate_url_wraps_the_item_url_with_the_configured_id(monkeypatch):
    monkeypatch.setenv("YAHOO_AFFILIATE_ID", "3123456")
    monkeypatch.setenv("YAHOO_AFFILIATE_PID", "887654321")
    from app.config import get_settings

    get_settings.cache_clear()

    result = yahoo.to_affiliate_url("https://store.shopping.yahoo.co.jp/example/g440.html")
    assert result is not None
    assert result.startswith("https://ck.jp.ap.valuecommerce.com/servlet/referral?sid=3123456&pid=887654321&vc_url=")
    assert "store.shopping.yahoo.co.jp%2Fexample%2Fg440.html" in result

    get_settings.cache_clear()


def test_product_out_wraps_plain_stored_yahoo_url():
    """Links stored before the IDs were set are wrapped when served."""
    import datetime

    from app import yahoo
    from app.schemas import ProductOut

    now = datetime.datetime(2026, 10, 10)
    base = dict(
        id=1, slug="x", name="x", brand="b", category="driver",
        current_price=None, previous_price=None, lowest_price=None,
        average_price=None, price_change_percent=None, buy_score="wait",
        buy_signal_score=None, history_span_days=0, buy_reason=None,
        pending_review=False, popularity_rank=None, popularity_updated_at=None,
        yahoo_price=1000, yahoo_updated_at=now,
        forecast_confidence=None, forecast_center_price=None,
        forecast_low_price=None, forecast_high_price=None,
        forecast_target_date=None, forecast_trend=None, forecast_reason=None,
        ai_title=None, ai_summary=None, ai_caution=None,
        created_at=now, updated_at=now,
    )
    plain = "https://store.shopping.yahoo.co.jp/shop/item.html"
    out = ProductOut.model_validate({**base, "yahoo_url": plain})
    assert out.yahoo_url == yahoo.to_affiliate_url(plain)
    assert out.yahoo_url.startswith(yahoo.AFFILIATE_LINK_BASE)
    # already wrapped -> unchanged (no double wrap)
    again = ProductOut.model_validate({**base, "yahoo_url": out.yahoo_url})
    assert again.yahoo_url == out.yahoo_url
    none = ProductOut.model_validate({**base, "yahoo_url": None})
    assert none.yahoo_url is None
