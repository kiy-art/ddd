"""Auto-discovers candidate products from Rakuten Ichiba category searches,
so the catalog can grow without every product being hand-researched and
CSV-imported first.

Most discovered products are still created with pending_review=True and
hidden from all public endpoints (see crud.list_products /
get_product_by_slug) until an admin approves it via POST
/admin/products/{id}/approve — a search result can be a used item, an
accessory, an unrelated product, or simply misclassified, and this
pipeline has no human checking that, unlike a manually-entered or
CSV-imported product.

A narrow, conservative slice is instead created with pending_review=False
(live immediately) - see _is_safe_to_auto_publish - so the catalog can
scale toward the volume a consumables-led strategy (dozens of golf balls,
not one driver) needs without every single item waiting on a human. This
only ever loosens which pending items skip the review queue; it never
loosens which candidates get discarded entirely (that's still
_looks_like_accessory/_looks_like_non_retail_listing/MIN_DISCOVERY_PRICE/
_match_brand, unchanged below).

Every candidate that does get created is stored under a cleaned "ブランド
＋型番" name (see app/title_cleaner.py), not the shop's own noisy listing
title - both so the catalog reads like a price-comparison site rather
than a scrape of ad copy, and because dedup against already-registered
products (existing_names below) is keyed on that cleaned name: two
listings of the same real product whose raw titles differ only in
promotional noise now collapse into the same product instead of each
registering as a separate row.
"""

import time
from typing import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import crud, models, rakuten, schemas, title_cleaner
# Brand recognition lives in app/brands.py (shared with app/popularity.py
# and app/title_cleaner.py, none of which need to import each other just
# for this) - BRAND_KEYWORDS is re-exported here so existing
# `from app.discovery import BRAND_KEYWORDS` call sites (see
# app/popularity.py) keep working unchanged.
from app.brands import BRAND_KEYWORDS, match_brand as _match_brand  # noqa: F401 (BRAND_KEYWORDS re-exported for app/popularity.py)
from app.pipeline import (
    RAKUTEN_REQUEST_INTERVAL_SECONDS,
    _looks_like_accessory,
    _looks_like_non_retail_listing,
    sync_product_analysis,
)

# One or more searches per category. Deliberately generic ("新品" = new,
# not used) rather than per-model for driver/iron/wedge/putter, since the
# goal there is finding products we don't have yet, not tracking a known
# one. Golf balls are the exception: a generic "ゴルフボール" search skews
# toward cheap no-name multi-packs, so specific perennial-bestseller model
# names are searched directly to reliably surface the models a golfer
# would actually search this site for (consumables strategy — see
# docs/ai_company_guidelines.md 3.5.5).
CATEGORY_SEARCH_KEYWORDS = {
    "driver": ["ゴルフ ドライバー 新品"],
    "iron": ["ゴルフ アイアン セット 新品"],
    "wedge": ["ゴルフ ウェッジ 新品"],
    "putter": ["ゴルフ パター 新品"],
    "ball": [
        "ゴルフボール 1ダース 新品",
        "Titleist Pro V1 ゴルフボール",
        "スリクソン Z-STAR ゴルフボール",
        "ブリヂストン TOUR B ゴルフボール",
    ],
}

# A real, currently-sold golf club or a dozen balls essentially never costs
# less than this — a cheap soft floor to catch obvious junk/accessory
# matches that _looks_like_accessory's keyword list doesn't happen to name.
MIN_DISCOVERY_PRICE = 3000

# Rakuten Ichiba Item Search API's own per-request maximum.
DISCOVERY_SEARCH_HITS = 30

# Cap new products added per category (summed across all of that
# category's keywords) per run: bounds Rakuten API usage and keeps a
# single run's growth reviewable-in-aggregate even though most of it no
# longer sits in the pending-review queue (see _is_safe_to_auto_publish).
MAX_NEW_PER_CATEGORY = 20


# Item-name substrings that make a candidate too likely to be a used item,
# a bare accessory, or a listing described relative to another product
# ("〇〇用") rather than being the product itself — checked in addition to
# (not instead of) _looks_like_accessory's own reject list above, since
# this one only decides whether an already-accepted candidate is safe to
# show a visitor immediately, not whether it's added at all. A match here
# never discards the candidate — it's still added, just as
# pending_review=True (the same "wait for a human" behavior every
# discovered product used to have) instead of live.
AUTO_PUBLISH_NG_KEYWORDS = [
    "中古",
    "ヘッドカバー",
    "シャフトのみ",
    "スリーブ",
    "用",
]

# Auto-publish price floor. Deliberately higher than MIN_DISCOVERY_PRICE
# (which only guards against being added at all) for clubs specifically:
# a driver/iron/wedge/putter priced under five figures is far more likely
# to be a mismatched/bundle-remainder listing than a genuinely cheap real
# club, so clubs get a stricter bar than balls before skipping review.
AUTO_PUBLISH_MIN_PRICE_BALL = 3000
AUTO_PUBLISH_MIN_PRICE_CLUB = 10000


def _is_safe_to_auto_publish(item_name: str, category: str, price: int) -> bool:
    """True only for a candidate safe enough to publish immediately,
    without a human checking it first. Everything else is still added to
    the catalog (as pending_review=True) — this only decides which
    already-accepted candidates skip that queue."""
    if any(keyword in item_name for keyword in AUTO_PUBLISH_NG_KEYWORDS):
        return False
    threshold = AUTO_PUBLISH_MIN_PRICE_BALL if category == "ball" else AUTO_PUBLISH_MIN_PRICE_CLUB
    return price >= threshold


def discover_new_products(
    db: Session, on_progress: Callable[[int, int], None] | None = None
) -> tuple[int, int]:
    """Searches each category's keyword(s) on Rakuten and creates a
    product for every candidate that passes every filter: not an
    accessory-looking listing, not implausibly cheap, a recognizable
    brand, and not already in the catalog (by listing URL or exact name).
    Most such candidates are created pending review (hidden from every
    public endpoint until an admin approves them); a narrow, conservative
    slice that also passes _is_safe_to_auto_publish is created live
    instead (see module docstring).

    `on_progress(current, total)`, when given, is called once per keyword
    search (1-indexed) - purely an optional progress report for the
    caller (see routers/admin.py + app/progress.py's live dashboard);
    omitting it changes nothing about this function's own behavior.

    Returns (discovered_count, considered_count)."""
    existing_products = list(db.execute(select(models.Product)).scalars().all())
    existing_urls = {p.affiliate_url for p in existing_products if p.affiliate_url}
    existing_urls |= {p.product_url for p in existing_products if p.product_url}
    # Keyed by the product's own (already-clean) stored name, since every
    # candidate below is compared against this by its OWN cleaned name too
    # (see title_cleaner.clean_product_title) - this is what actually makes
    # "同じ型番の商品は1つに統合" work: two listings whose raw shop titles
    # differ only in promotional noise clean down to the same name and so
    # collapse to a single dedup hit here, instead of both slipping through
    # as "different" products the way comparing raw titles would.
    existing_names = {(p.brand.strip().lower(), p.name.strip().lower()) for p in existing_products}

    total_keywords = sum(len(keywords) for keywords in CATEGORY_SEARCH_KEYWORDS.values())
    discovered = 0
    considered = 0
    request_index = 0
    for category, keywords in CATEGORY_SEARCH_KEYWORDS.items():
        added_this_category = 0
        for keyword in keywords:
            # Once a category's cap is reached, its remaining keywords are
            # skipped entirely (no request made) - but still counted
            # toward on_progress's total, so a live progress bar built
            # from (request_index, total_keywords) always reaches 100%.
            if added_this_category < MAX_NEW_PER_CATEGORY:
                if request_index > 0:
                    time.sleep(RAKUTEN_REQUEST_INTERVAL_SECONDS)
                try:
                    items = rakuten.search_items(keyword, hits=DISCOVERY_SEARCH_HITS)
                except Exception as exc:  # noqa: BLE001 - keep discovering other keywords/categories
                    crud.create_error_log(db, source="discovery", message=f"{keyword}: {exc}")
                    items = []

                for item in items:
                    if added_this_category >= MAX_NEW_PER_CATEGORY:
                        break
                    considered += 1

                    if _looks_like_accessory(item.item_name):
                        continue
                    if _looks_like_non_retail_listing(item.item_name):
                        continue
                    if item.price < MIN_DISCOVERY_PRICE:
                        continue
                    if item.item_url in existing_urls:
                        continue
                    brand = _match_brand(item.item_name)
                    if brand is None:
                        continue

                    # Cleaned (not the raw shop title) both for what gets
                    # stored and for the dedup check right below - see
                    # existing_names above for why this is what makes
                    # "same model, noisier title" collapse into one product
                    # instead of registering as a second one.
                    clean_name = title_cleaner.clean_product_title(item.item_name, brand, category)
                    name_key = (brand.strip().lower(), clean_name.strip().lower())
                    if name_key in existing_names:
                        continue

                    # Checked against the raw title, not clean_name: title
                    # cleaning can legitimately shorten "PING G440 中古
                    # ドライバー" down toward just "PING G440 ドライバー"
                    # (the same way it drops "送料無料"), which must never
                    # cause the NG-word check below to miss "中古" and
                    # auto-publish a used item.
                    pending_review = not _is_safe_to_auto_publish(item.item_name, category, item.price)
                    product = crud.create_product(
                        db,
                        schemas.ProductCreate(
                            name=clean_name,
                            brand=brand,
                            category=category,
                            image_url=item.image_url,
                            product_url=item.item_url,
                            affiliate_url=rakuten.to_affiliate_url(item.item_url) or item.item_url,
                            initial_price=item.price,
                        ),
                        pending_review=pending_review,
                    )
                    sync_product_analysis(db, product)

                    existing_urls.add(item.item_url)
                    existing_names.add(name_key)
                    discovered += 1
                    added_this_category += 1

            request_index += 1
            if on_progress is not None:
                on_progress(request_index, total_keywords)

    return discovered, considered
