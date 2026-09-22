import httpx
import pytest

from app import rakuten


def test_raises_when_app_id_missing(monkeypatch):
    monkeypatch.setenv("RAKUTEN_APP_ID", "")
    monkeypatch.setenv("RAKUTEN_ACCESS_KEY", "")
    from app.config import get_settings

    get_settings.cache_clear()
    with pytest.raises(rakuten.RakutenNotConfigured):
        rakuten.search_lowest_price("PING G440")
    get_settings.cache_clear()


def test_raises_when_access_key_missing(monkeypatch):
    monkeypatch.setenv("RAKUTEN_APP_ID", "test-app-id")
    monkeypatch.setenv("RAKUTEN_ACCESS_KEY", "")
    from app.config import get_settings

    get_settings.cache_clear()
    with pytest.raises(rakuten.RakutenNotConfigured):
        rakuten.search_lowest_price("PING G440")
    get_settings.cache_clear()


def test_search_lowest_price_returns_first_result(monkeypatch):
    monkeypatch.setenv("RAKUTEN_APP_ID", "test-app-id")
    monkeypatch.setenv("RAKUTEN_ACCESS_KEY", "test-access-key")
    from app.config import get_settings

    get_settings.cache_clear()

    payload = {
        "Items": [
            {
                "Item": {
                    "itemName": "PING G440 ドライバー",
                    "itemPrice": 68000,
                    "itemUrl": "https://item.rakuten.co.jp/example/g440/",
                    "mediumImageUrls": [{"imageUrl": "https://thumbnail.image.rakuten.co.jp/x.jpg?_ex=1"}],
                }
            }
        ]
    }

    def fake_get(url, params=None, headers=None, timeout=None):
        assert params["applicationId"] == "test-app-id"
        assert params["accessKey"] == "test-access-key"
        assert params["keyword"] == "PING G440"
        assert headers.get("Referer")
        return httpx.Response(200, json=payload, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)

    result = rakuten.search_lowest_price("PING G440")
    assert result is not None
    assert result.price == 68000
    assert result.item_url == "https://item.rakuten.co.jp/example/g440/"
    assert result.image_url == "https://thumbnail.image.rakuten.co.jp/x.jpg"

    get_settings.cache_clear()


def test_search_lowest_price_picks_median_over_outlier(monkeypatch):
    """A junk/irrelevant listing (e.g. a loose part) far below the real
    product's price must not be picked just because it's cheapest — this is
    the exact bug that caused a PING G430 iron to show a fake ¥1,100 price."""
    monkeypatch.setenv("RAKUTEN_APP_ID", "test-app-id")
    monkeypatch.setenv("RAKUTEN_ACCESS_KEY", "test-access-key")
    from app.config import get_settings

    get_settings.cache_clear()

    def make_item(name, price, path):
        return {
            "Item": {
                "itemName": name,
                "itemPrice": price,
                "itemUrl": f"https://item.rakuten.co.jp/example/{path}/",
                "mediumImageUrls": [],
            }
        }

    payload = {
        "Items": [
            make_item("PING G430 用 交換パーツ", 1100, "junk"),
            make_item("PING G430 アイアン セット", 58000, "a"),
            make_item("PING G430 アイアン", 60000, "b"),
            make_item("PING G430 アイアン 中古美品", 62000, "c"),
        ]
    }

    def fake_get(url, params=None, headers=None, timeout=None):
        assert "sort" not in params  # no cheapest-first sort
        return httpx.Response(200, json=payload, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)

    result = rakuten.search_lowest_price("PING G430")
    assert result is not None
    assert result.price == 60000  # closest to the median, not the ¥1,100 outlier
    get_settings.cache_clear()


def test_search_lowest_price_returns_none_when_no_items(monkeypatch):
    monkeypatch.setenv("RAKUTEN_APP_ID", "test-app-id")
    monkeypatch.setenv("RAKUTEN_ACCESS_KEY", "test-access-key")
    from app.config import get_settings

    get_settings.cache_clear()

    def fake_get(url, params=None, headers=None, timeout=None):
        return httpx.Response(200, json={"Items": []}, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)

    assert rakuten.search_lowest_price("nonexistent item xyz") is None
    get_settings.cache_clear()


def test_fetch_ranking_raises_when_app_id_missing(monkeypatch):
    monkeypatch.setenv("RAKUTEN_APP_ID", "")
    from app.config import get_settings

    get_settings.cache_clear()
    with pytest.raises(rakuten.RakutenNotConfigured):
        rakuten.fetch_ranking(201706)
    get_settings.cache_clear()


def test_fetch_ranking_parses_items_in_rank_order(monkeypatch):
    monkeypatch.setenv("RAKUTEN_APP_ID", "test-app-id")
    from app.config import get_settings

    get_settings.cache_clear()

    payload = {
        "Items": [
            {"Item": {"rank": 1, "itemName": "PING G440 ドライバー", "itemUrl": "https://item.rakuten.co.jp/a/"}},
            {"Item": {"rank": 2, "itemName": "テーラーメイド Qi35 ドライバー", "itemUrl": "https://item.rakuten.co.jp/b/"}},
        ]
    }

    def fake_get(url, params=None, headers=None, timeout=None):
        assert url == rakuten.RANKING_URL
        assert params["applicationId"] == "test-app-id"
        assert params["genreId"] == 201706
        return httpx.Response(200, json=payload, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)

    results = rakuten.fetch_ranking(201706)
    assert [r.rank for r in results] == [1, 2]
    assert results[0].item_name == "PING G440 ドライバー"

    get_settings.cache_clear()


def test_fetch_ranking_skips_malformed_entries(monkeypatch):
    monkeypatch.setenv("RAKUTEN_APP_ID", "test-app-id")
    from app.config import get_settings

    get_settings.cache_clear()

    payload = {"Items": [{"Item": {"itemName": "missing rank/url fields"}}]}

    def fake_get(url, params=None, headers=None, timeout=None):
        return httpx.Response(200, json=payload, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)

    assert rakuten.fetch_ranking(201706) == []
    get_settings.cache_clear()


def test_to_affiliate_url_returns_none_when_not_configured(monkeypatch):
    monkeypatch.setenv("RAKUTEN_AFFILIATE_ID", "")
    from app.config import get_settings

    get_settings.cache_clear()
    assert rakuten.to_affiliate_url("https://item.rakuten.co.jp/example/g440/") is None
    get_settings.cache_clear()


def test_to_affiliate_url_wraps_the_item_url_with_the_configured_id(monkeypatch):
    monkeypatch.setenv("RAKUTEN_AFFILIATE_ID", "38e4bda3.3d4c8086.38e4bda4.cefadc6a")
    from app.config import get_settings

    get_settings.cache_clear()

    result = rakuten.to_affiliate_url("https://item.rakuten.co.jp/example/g440/")
    assert result is not None
    assert result.startswith(
        "https://hb.afl.rakuten.co.jp/ichiba/38e4bda3.3d4c8086.38e4bda4.cefadc6a/?pc="
    )
    assert "item.rakuten.co.jp%2Fexample%2Fg440%2F" in result
    assert rakuten.is_affiliate_link(result)
    assert not rakuten.is_affiliate_link("https://item.rakuten.co.jp/example/g440/")

    get_settings.cache_clear()
