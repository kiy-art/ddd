"""Client for the Rakuten Ichiba Item Search API (楽天市場商品検索API).

Free, no-affiliate-approval-required API — just a Rakuten Developers
"Application ID". Used as the MVP's live price source so daily updates
don't rely on scraping (see README section 10 on data acquisition policy).

https://webservice.rakuten.co.jp/documentation/ichiba-item-search
"""

import urllib.parse

import httpx

from app.config import get_settings

SEARCH_URL = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701"
AFFILIATE_LINK_BASE = "https://hb.afl.rakuten.co.jp/ichiba"


class RakutenNotConfigured(Exception):
    pass


class RakutenSearchResult:
    def __init__(self, price: int, item_url: str, image_url: str | None, item_name: str):
        self.price = price
        self.item_url = item_url
        self.image_url = image_url
        self.item_name = item_name


def to_affiliate_url(item_url: str) -> str | None:
    """Wraps a plain Rakuten Ichiba item URL in this site's affiliate
    tracking link, so a purchase through it earns a commission. Returns
    None (caller keeps the plain URL) when RAKUTEN_AFFILIATE_ID isn't set -
    registering for Rakuten Affiliate is a manual, one-time step (see
    README), not something this app can do for itself."""
    settings = get_settings()
    if not settings.rakuten_affiliate_id:
        return None
    encoded = urllib.parse.quote(item_url, safe="")
    return f"{AFFILIATE_LINK_BASE}/{settings.rakuten_affiliate_id}/?pc={encoded}&link_type=hybrid_url"


def is_affiliate_link(url: str) -> bool:
    return url.startswith(AFFILIATE_LINK_BASE)


def _item_to_result(item: dict) -> RakutenSearchResult:
    images = item.get("mediumImageUrls") or []
    image_url = images[0].get("imageUrl") if images else None
    # Rakuten returns tracking-wrapped thumbnail URLs; strip the query string
    if image_url and "?" in image_url:
        image_url = image_url.split("?", 1)[0]

    return RakutenSearchResult(
        price=int(item["itemPrice"]),
        item_url=item["itemUrl"],
        image_url=image_url,
        item_name=item["itemName"],
    )


def _fetch_candidates(keyword: str, hits: int, timeout: float) -> list[dict]:
    settings = get_settings()
    if not settings.rakuten_app_id:
        raise RakutenNotConfigured("RAKUTEN_APP_ID is not configured")
    if not settings.rakuten_access_key:
        raise RakutenNotConfigured("RAKUTEN_ACCESS_KEY is not configured")

    params = {
        "applicationId": settings.rakuten_app_id,
        "accessKey": settings.rakuten_access_key,
        "keyword": keyword,
        "format": "json",
        "hits": hits,
        "availability": 1,
        # No explicit sort: Rakuten's default "standard" relevance ranking.
        # We used to sort by cheapest price first, but that preferentially
        # matched irrelevant/junk listings (a loose part, an accessory, a
        # mis-tagged item) far below the real product's price — see the
        # incident where a PING G430 iron briefly showed a fake ¥1,100.
    }
    # The "Web Application" app type validates requests by HTTP Referer/Origin
    # against the registered "Allowed websites" list, which server-to-server
    # calls don't send by default — so we set both explicitly. (Referer alone
    # isn't enough; Rakuten's gateway checks Origin too.)
    headers = (
        {"Referer": settings.rakuten_referer, "Origin": settings.rakuten_referer}
        if settings.rakuten_referer
        else {}
    )

    response = httpx.get(SEARCH_URL, params=params, headers=headers, timeout=timeout)
    if response.is_error:
        raise RuntimeError(f"Rakuten API {response.status_code}: {response.text[:500]}")
    data = response.json()

    items = data.get("Items") or []
    return [it["Item"] for it in items]


def search_lowest_price(keyword: str, timeout: float = 10.0) -> RakutenSearchResult | None:
    """Returns the single listing closest to the median price among the top
    matches for `keyword` (a mismatch-resistant pick for tracking one known
    product's price), or None if nothing matched."""
    candidates = _fetch_candidates(keyword, hits=10, timeout=timeout)
    if not candidates:
        return None

    # Pick the candidate closest to the median price among the results,
    # instead of blindly trusting whichever the API ranks first. This
    # guards against a single outlier listing (an unrelated cheap
    # accessory, or an overpriced bundle) being mistaken for the product.
    prices = sorted(c["itemPrice"] for c in candidates)
    median_price = prices[len(prices) // 2]
    item = min(candidates, key=lambda c: abs(c["itemPrice"] - median_price))
    return _item_to_result(item)


def search_items(keyword: str, hits: int = 10, timeout: float = 10.0) -> list[RakutenSearchResult]:
    """Returns every matched listing for `keyword` (up to `hits`), unreduced
    — for discovering new candidate products rather than pricing one known
    product."""
    candidates = _fetch_candidates(keyword, hits=hits, timeout=timeout)
    return [_item_to_result(item) for item in candidates]
