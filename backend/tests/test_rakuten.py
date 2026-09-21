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

    def fake_get(url, params=None, timeout=None):
        assert params["applicationId"] == "test-app-id"
        assert params["accessKey"] == "test-access-key"
        assert params["keyword"] == "PING G440"
        return httpx.Response(200, json=payload, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)

    result = rakuten.search_lowest_price("PING G440")
    assert result is not None
    assert result.price == 68000
    assert result.item_url == "https://item.rakuten.co.jp/example/g440/"
    assert result.image_url == "https://thumbnail.image.rakuten.co.jp/x.jpg"

    get_settings.cache_clear()


def test_search_lowest_price_returns_none_when_no_items(monkeypatch):
    monkeypatch.setenv("RAKUTEN_APP_ID", "test-app-id")
    monkeypatch.setenv("RAKUTEN_ACCESS_KEY", "test-access-key")
    from app.config import get_settings

    get_settings.cache_clear()

    def fake_get(url, params=None, timeout=None):
        return httpx.Response(200, json={"Items": []}, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)

    assert rakuten.search_lowest_price("nonexistent item xyz") is None
    get_settings.cache_clear()
