"""Auto-discovers candidate products from Rakuten Ichiba category searches,
so the catalog can grow without every product being hand-researched and
CSV-imported first.

Every discovered product is created with pending_review=True and is hidden
from all public endpoints (see crud.list_products / get_product_by_slug)
until an admin approves it via POST /admin/products/{id}/approve. Nothing
here is ever shown to a site visitor un-reviewed — a search result can be
a used item, an accessory, an unrelated product, or simply misclassified,
and this pipeline has no human checking that, unlike a manually-entered or
CSV-imported product.
"""

import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import crud, models, rakuten, schemas
from app.pipeline import RAKUTEN_REQUEST_INTERVAL_SECONDS, _looks_like_accessory, sync_product_analysis

# One representative search per category. Deliberately generic ("新品" =
# new, not used) rather than per-brand/per-model, since the goal is finding
# products we don't have yet, not tracking a known one.
CATEGORY_SEARCH_KEYWORDS = {
    "driver": "ゴルフ ドライバー 新品",
    "iron": "ゴルフ アイアン セット 新品",
    "wedge": "ゴルフ ウェッジ 新品",
    "putter": "ゴルフ パター 新品",
    "ball": "ゴルフボール 1ダース",
}

# A real, currently-sold golf club or a dozen balls essentially never costs
# less than this — a cheap soft floor to catch obvious junk/accessory
# matches that _looks_like_accessory's keyword list doesn't happen to name.
MIN_DISCOVERY_PRICE = 3000

# Cap new products added per category per run: keeps the pending-review
# queue reviewable and bounds Rakuten API usage (this runs alongside the
# existing per-product price fetch, which already uses one request per
# product under the API's ~1 req/sec free-tier limit).
MAX_NEW_PER_CATEGORY = 3

# Maps a keyword that might appear in a Rakuten item name (English brand
# name or a common Japanese rendering) to this site's canonical brand name
# (matching the brand strings already used across data/*.csv). A listing
# whose name matches none of these is skipped — better to miss a real
# product than to publish one under a guessed/wrong brand.
BRAND_KEYWORDS = {
    "PING": "PING",
    "ピン": "PING",
    "Titleist": "Titleist",
    "タイトリスト": "Titleist",
    "Callaway": "Callaway",
    "キャロウェイ": "Callaway",
    "TaylorMade": "TaylorMade",
    "テーラーメイド": "TaylorMade",
    "Srixon": "Srixon",
    "スリクソン": "Srixon",
    "Bridgestone": "Bridgestone",
    "ブリヂストン": "Bridgestone",
    "ブリジストン": "Bridgestone",
    "Cobra": "Cobra",
    "コブラ": "Cobra",
    "Mizuno": "Mizuno",
    "ミズノ": "Mizuno",
    "XXIO": "XXIO",
    "ゼクシオ": "XXIO",
    "Honma": "Honma",
    "ホンマ": "Honma",
    "Vokey": "Vokey",
    "ボーケイ": "Vokey",
    "Scotty Cameron": "Scotty Cameron",
    "スコッティキャメロン": "Scotty Cameron",
    "スコッティ・キャメロン": "Scotty Cameron",
    "Odyssey": "Odyssey",
    "オデッセイ": "Odyssey",
    "Cleveland": "Cleveland",
    "クリーブランド": "Cleveland",
}


def _match_brand(item_name: str) -> str | None:
    lowered = item_name.lower()
    for keyword, brand in BRAND_KEYWORDS.items():
        if keyword.lower() in lowered:
            return brand
    return None


def discover_new_products(db: Session) -> tuple[int, int]:
    """Searches each category's keyword on Rakuten and creates a pending
    (unpublished) product for candidates that pass every filter: not an
    accessory-looking listing, not implausibly cheap, a recognizable brand,
    and not already in the catalog (by listing URL or exact name).

    Returns (discovered_count, considered_count)."""
    existing_products = list(db.execute(select(models.Product)).scalars().all())
    existing_urls = {p.affiliate_url for p in existing_products if p.affiliate_url}
    existing_urls |= {p.product_url for p in existing_products if p.product_url}
    existing_names = {p.name.strip().lower() for p in existing_products}

    discovered = 0
    considered = 0
    for i, (category, keyword) in enumerate(CATEGORY_SEARCH_KEYWORDS.items()):
        if i > 0:
            time.sleep(RAKUTEN_REQUEST_INTERVAL_SECONDS)
        try:
            items = rakuten.search_items(keyword, hits=10)
        except Exception as exc:  # noqa: BLE001 - keep discovering other categories
            crud.create_error_log(db, source="discovery", message=f"{keyword}: {exc}")
            continue

        added_this_category = 0
        for item in items:
            if added_this_category >= MAX_NEW_PER_CATEGORY:
                break
            considered += 1

            if _looks_like_accessory(item.item_name):
                continue
            if item.price < MIN_DISCOVERY_PRICE:
                continue
            if item.item_url in existing_urls:
                continue
            name_key = item.item_name.strip().lower()
            if name_key in existing_names:
                continue
            brand = _match_brand(item.item_name)
            if brand is None:
                continue

            product = crud.create_product(
                db,
                schemas.ProductCreate(
                    name=item.item_name,
                    brand=brand,
                    category=category,
                    image_url=item.image_url,
                    product_url=item.item_url,
                    affiliate_url=item.item_url,
                    initial_price=item.price,
                ),
                pending_review=True,
            )
            sync_product_analysis(db, product)

            existing_urls.add(item.item_url)
            existing_names.add(name_key)
            discovered += 1
            added_this_category += 1

    return discovered, considered
