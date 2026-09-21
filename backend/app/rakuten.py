"""Client for the Rakuten Ichiba Item Search API (楽天市場商品検索API).

Free, no-affiliate-approval-required API — just a Rakuten Developers
"Application ID". Used as the MVP's live price source so daily updates
don't rely on scraping (see README section 10 on data acquisition policy).

https://webservice.rakuten.co.jp/documentation/ichiba-item-search
"""

import httpx

from app.config import get_settings

SEARCH_URL = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701"


class RakutenNotConfigured(Exception):
    pass


class RakutenSearchResult:
    def __init__(self, price: int, item_url: str, image_url: str | None, item_name: str):
        self.price = price
        self.item_url = item_url
        self.image_url = image_url
        self.item_name = item_name


def search_lowest_price(keyword: str, timeout: float = 10.0) -> RakutenSearchResult | None:
    """Returns the cheapest in-stock listing for `keyword`, or None if nothing matched."""
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
        "hits": 5,
        "availability": 1,
        "sort": "+itemPrice",
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
    if not items:
        return None

    item = items[0]["Item"]
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
