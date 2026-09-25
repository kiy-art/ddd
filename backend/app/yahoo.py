"""Client for the Yahoo!ショッピング商品検索API (Shopping Item Search API v3).

Free, no-affiliate-approval-required API - just a Yahoo! JAPAN Developer
Network "Client ID" (registered with "ID連携を利用しない", since this is a
plain keyed search endpoint, not a login/store-management API). Used as a
second, independent price source alongside Rakuten (see rakuten.py) so the
store comparison table can show a real second row instead of a fabricated
one.

https://developer.yahoo.co.jp/webapi/shopping/shopping/v3/itemsearch.html
"""

import urllib.parse

from app import http_retry
from app.config import get_settings

SEARCH_URL = "https://shopping.yahooapis.jp/ShoppingWebService/V3/itemSearch"
AFFILIATE_LINK_BASE = "https://ck.jp.ap.valuecommerce.com/servlet/referral"


class YahooNotConfigured(Exception):
    pass


class YahooSearchResult:
    def __init__(self, price: int, item_url: str, image_url: str | None, item_name: str):
        self.price = price
        self.item_url = item_url
        self.image_url = image_url
        self.item_name = item_name


def to_affiliate_url(item_url: str) -> str | None:
    """Wraps a plain Yahoo!ショッピング item URL in this site's ValueCommerce
    affiliate tracking link. Returns None (caller keeps the plain URL) when
    YAHOO_AFFILIATE_ID isn't set - that's a separate, manual registration
    step (ValueCommerce or Yahoo!アフィリエイト), same as Rakuten Affiliate."""
    settings = get_settings()
    if not settings.yahoo_affiliate_id:
        return None
    encoded = urllib.parse.quote(item_url, safe="")
    return f"{AFFILIATE_LINK_BASE}?sid={settings.yahoo_affiliate_id}&pid=&vc_url={encoded}"


def _item_to_result(item: dict) -> YahooSearchResult:
    image = item.get("image") or {}
    image_url = image.get("medium") or image.get("small")

    return YahooSearchResult(
        price=int(item["price"]),
        item_url=item["url"],
        image_url=image_url,
        item_name=item["name"],
    )


def _fetch_candidates(keyword: str, hits: int, timeout: float) -> list[dict]:
    settings = get_settings()
    if not settings.yahoo_client_id:
        raise YahooNotConfigured("YAHOO_CLIENT_ID is not configured")

    params = {
        "appid": settings.yahoo_client_id,
        "query": keyword,
        "results": hits,
        "in_stock": "true",
        # No explicit sort (default relevance), matching rakuten.py's own
        # reasoning: sorting by cheapest price first preferentially matches
        # irrelevant/junk listings (an accessory, a mis-tagged item) instead
        # of the actual product.
    }

    response = http_retry.get_with_retry(SEARCH_URL, params=params, timeout=timeout)
    if response.is_error:
        raise RuntimeError(f"Yahoo Shopping API {response.status_code}: {response.text[:500]}")
    data = response.json()

    hits_list = data.get("hits") or []
    # See rakuten.py's matching filter: a small fraction of listings omit
    # price/url/name (found while investigating STEP34's error-log volume).
    return [h for h in hits_list if "price" in h and "url" in h and "name" in h]


def search_lowest_price(keyword: str, timeout: float = 10.0) -> YahooSearchResult | None:
    """Same mismatch-resistant "closest to median" pick as
    rakuten.search_lowest_price, for the same reason: a single outlier
    listing shouldn't be mistaken for the product's real price."""
    candidates = _fetch_candidates(keyword, hits=10, timeout=timeout)
    if not candidates:
        return None

    prices = sorted(int(c["price"]) for c in candidates)
    median_price = prices[len(prices) // 2]
    item = min(candidates, key=lambda c: abs(int(c["price"]) - median_price))
    return _item_to_result(item)
