"""Client for the Rakuten Ichiba Item Search API (楽天市場商品検索API).

Free, no-affiliate-approval-required API — just a Rakuten Developers
"Application ID". Used as the MVP's live price source so daily updates
don't rely on scraping (see README section 10 on data acquisition policy).

https://webservice.rakuten.co.jp/documentation/ichiba-item-search
"""

import urllib.parse

from app import http_retry, iron_sets
from app.config import get_settings

SEARCH_URL = "https://openapi.rakuten.co.jp/ichibams/api/IchibaItem/Search/20260701"
RANKING_URL = "https://openapi.rakuten.co.jp/ichibaranking/api/IchibaItem/Ranking/20220601"
AFFILIATE_LINK_BASE = "https://hb.afl.rakuten.co.jp/ichiba"


class RakutenNotConfigured(Exception):
    pass


class RakutenSearchResult:
    def __init__(self, price: int, item_url: str, image_url: str | None, item_name: str, caption: str | None = None):
        self.price = price
        self.item_url = item_url
        self.image_url = image_url
        self.item_name = item_name
        # STEP61: the shop's own item description - the source of the spec
        # table (loft, shaft, ...) parsed by app/spec_extractor.py.
        self.caption = caption


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
        caption=item.get("itemCaption") or None,
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

    response = http_retry.get_with_retry(SEARCH_URL, params=params, headers=headers, timeout=timeout)
    if response.is_error:
        raise RuntimeError(f"Rakuten API {response.status_code}: {response.text[:500]}")
    data = response.json()

    items = data.get("Items") or []
    candidates = [it["Item"] for it in items]
    # A small fraction of listings omit itemPrice/itemUrl/itemName (e.g. an
    # inquiry-only or delisted item still returned in search results).
    # Dropped here rather than left to crash _item_to_result with a bare
    # KeyError deep in a per-product batch loop (see app/pipeline.py) -
    # found while investigating STEP34's accumulated error-log count.
    return [c for c in candidates if "itemPrice" in c and "itemUrl" in c and "itemName" in c]


# Irons need more candidates than other categories: most matches for a
# model name are single irons or selectable "1本 3本 5本 6本" listings, and
# only the 5-6本 sets among them are kept (see app/iron_sets.py).
IRON_SEARCH_HITS = 30


def _iron_set_candidates(keyword: str, fetch) -> list[dict]:
    """5-6本 set listings for `keyword`, retrying once with "セット" added
    when the plain search returned none (a model whose top matches are all
    single irons). `fetch(keyword)` returns raw candidate dicts."""
    sets = [c for c in fetch(keyword) if iron_sets.is_standard_set(c["itemName"])]
    if not sets:
        sets = [c for c in fetch(f"{keyword} セット") if iron_sets.is_standard_set(c["itemName"])]
    return sets


def _closest_to_median(candidates: list[dict]) -> dict:
    # Pick the candidate closest to the median price among the results,
    # instead of blindly trusting whichever the API ranks first. This
    # guards against a single outlier listing (an unrelated cheap
    # accessory, or an overpriced bundle) being mistaken for the product.
    prices = sorted(c["itemPrice"] for c in candidates)
    median_price = prices[len(prices) // 2]
    return min(candidates, key=lambda c: abs(c["itemPrice"] - median_price))


def search_lowest_price(
    keyword: str, timeout: float = 10.0, category: str | None = None
) -> RakutenSearchResult | None:
    """Returns the single listing closest to the median price among the top
    matches for `keyword` (a mismatch-resistant pick for tracking one known
    product's price), or None if nothing matched.

    category="iron": only 5-6本 set listings count (社長指示 2026-10-10 -
    a single-iron price made a set look absurdly cheap); None when no set
    listing matched, so the caller skips rather than records a single."""
    if category == "iron":
        candidates = _iron_set_candidates(
            keyword, lambda kw: _fetch_candidates(kw, hits=IRON_SEARCH_HITS, timeout=timeout)
        )
    else:
        candidates = _fetch_candidates(keyword, hits=10, timeout=timeout)
    if not candidates:
        return None
    return _item_to_result(_closest_to_median(candidates))


def search_items(keyword: str, hits: int = 10, timeout: float = 10.0) -> list[RakutenSearchResult]:
    """Returns every matched listing for `keyword` (up to `hits`), unreduced
    — for discovering new candidate products rather than pricing one known
    product."""
    candidates = _fetch_candidates(keyword, hits=hits, timeout=timeout)
    return [_item_to_result(item) for item in candidates]


class RakutenRankingItem:
    def __init__(
        self,
        rank: int,
        item_name: str,
        item_url: str,
        price: int | None = None,
        image_url: str | None = None,
        shop_name: str | None = None,
        review_count: int | None = None,
        review_average: float | None = None,
    ):
        self.rank = rank
        self.item_name = item_name
        self.item_url = item_url
        # STEP59: the rest of what the ranking API returns per listing, so
        # the popularity page can show Rakuten's own ranking list itself.
        self.price = price
        self.image_url = image_url
        self.shop_name = shop_name
        self.review_count = review_count
        self.review_average = review_average


def _ranking_image(item: dict) -> str | None:
    images = item.get("mediumImageUrls") or []
    first = images[0] if images else None
    url = first.get("imageUrl") if isinstance(first, dict) else first
    if not url:
        return None
    # The API's thumbnails are 128px; ask the same CDN for a card-sized one.
    return url.replace("_ex=128x128", "_ex=300x300")


def _optional_int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def fetch_ranking(genre_id: int, hits: int = 30, timeout: float = 10.0) -> list[RakutenRankingItem]:
    """Rakuten's own real-time bestseller ranking for a genre (see
    https://webservice.rakuten.co.jp/documentation/ichiba-item-ranking) -
    an actual third-party "what's popular right now" signal, not something
    this site computes or guesses. Returns [] (never raises past logging by
    the caller) is the caller's job on request failure - this function
    itself still raises so a bad genreId/network error is visible."""
    settings = get_settings()
    if not settings.rakuten_app_id:
        raise RakutenNotConfigured("RAKUTEN_APP_ID is not configured")
    if not settings.rakuten_access_key:
        raise RakutenNotConfigured("RAKUTEN_ACCESS_KEY is not configured")

    # The 2026 Rakuten Web Service platform (openapi.rakuten.co.jp) rejects
    # any request that doesn't carry BOTH applicationId and accessKey - the
    # same as the item search above. This call used to send applicationId
    # only, so every daily ranking sync failed and the site kept showing
    # whatever ranks it had last stored (STEP51).
    params = {
        "applicationId": settings.rakuten_app_id,
        "accessKey": settings.rakuten_access_key,
        "genreId": genre_id,
        "format": "json",
    }
    headers = (
        {"Referer": settings.rakuten_referer, "Origin": settings.rakuten_referer}
        if settings.rakuten_referer
        else {}
    )

    response = http_retry.get_with_retry(RANKING_URL, params=params, headers=headers, timeout=timeout)
    if response.is_error:
        raise RuntimeError(f"Rakuten Ranking API {response.status_code}: {response.text[:500]}")
    data = response.json()

    items = data.get("Items") or []
    results = []
    for entry in items[:hits]:
        item = entry.get("Item", entry)
        try:
            results.append(
                RakutenRankingItem(
                    rank=int(item["rank"]),
                    item_name=item["itemName"],
                    item_url=item["itemUrl"],
                    price=_optional_int(item.get("itemPrice")),
                    image_url=_ranking_image(item),
                    shop_name=item.get("shopName") or None,
                    review_count=_optional_int(item.get("reviewCount")),
                    review_average=_optional_float(item.get("reviewAverage")),
                )
            )
        except (KeyError, ValueError, TypeError):
            continue  # unexpected shape for this entry - skip it, keep the rest
    return results
