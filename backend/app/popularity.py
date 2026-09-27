"""Syncs each tracked product's real-time Rakuten Ichiba bestseller rank
(see app/rakuten.py:fetch_ranking) onto Product.popularity_rank.

This is a genuine third-party "what's actually selling well right now"
signal - Rakuten's own ranking, not something this site infers or
fabricates from its own (still very low) traffic. Combined with
price_change_percent/forecast_trend, it answers the question this feature
exists for: "this club is popular, but has the price actually been
dropping?" - a real cross-signal, not two separately-plausible-looking
numbers stapled together.
"""

import datetime
import re
import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import crud, models, rakuten, title_cleaner
from app.brands import match_brand as _match_brand
from app.pipeline import RAKUTEN_REQUEST_INTERVAL_SECONDS

# Rakuten Ichiba's own genre IDs for each category, found via
# ranking.rakuten.co.jp (each category's ranking page URL embeds its
# genreId) - see ranking.rakuten.co.jp/daily/<id>/.
CATEGORY_GENRE_IDS = {
    "driver": 201706,
    "iron": 201725,
    "wedge": 204934,
    "putter": 201744,
    "ball": 204964,
}

# How many ranking positions to pull per category. Rakuten's ranking is a
# real ordered list of actual listings, mostly dominated by whatever's
# cheapest/most-reviewed at that moment - pulling more positions gives a
# better chance of finding our specific tracked model in it.
RANKING_HITS = 30


def _normalize(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


def _find_rank(product: models.Product, ranking_items: list) -> int | None:
    """First (best) ranking-list position whose item name plausibly names
    this product: same brand, and (when we know a model number) the model
    number appears in the listing's name. Without a model number, matching
    on brand alone is too weak (a listing can share a brand without being
    this product), so those products are simply never ranked."""
    if not product.model_number:
        return None
    model_key = _normalize(product.model_number)
    for entry in ranking_items:
        if _match_brand(entry.item_name) != product.brand:
            continue
        if model_key in _normalize(entry.item_name):
            return entry.rank
    return None


# STEP59: a stored ranking snapshot older than this isn't "popular now" -
# same window as the per-product ranks (frontend lib/popularity.ts).
RANKING_MAX_AGE_DAYS = 3


def _matched_product_id(entry, products: list[models.Product]) -> int | None:
    """The catalog product this ranking listing is, by the same rule as
    _find_rank (same brand + the product's model number in the name)."""
    brand = _match_brand(entry.item_name)
    if brand is None:
        return None
    name_key = _normalize(entry.item_name)
    for product in products:
        if product.brand == brand and product.model_number and _normalize(product.model_number) in name_key:
            return product.id
    return None


def _store_ranking_snapshot(db: Session, category: str, ranking_items: list, products: list[models.Product]) -> None:
    """Replaces this category's stored copy of Rakuten's ranking list."""
    now = datetime.datetime.utcnow()
    db.query(models.RakutenRankingEntry).filter(models.RakutenRankingEntry.category == category).delete()
    for entry in ranking_items:
        brand = _match_brand(entry.item_name)
        db.add(
            models.RakutenRankingEntry(
                category=category,
                rank=entry.rank,
                item_name=entry.item_name,
                display_name=title_cleaner.strip_promotional_noise(entry.item_name, brand=brand)[:300],
                brand=brand,
                price=getattr(entry, "price", None),
                item_url=entry.item_url,
                affiliate_url=rakuten.to_affiliate_url(entry.item_url),
                image_url=getattr(entry, "image_url", None),
                shop_name=getattr(entry, "shop_name", None),
                review_count=getattr(entry, "review_count", None),
                review_average=getattr(entry, "review_average", None),
                matched_product_id=_matched_product_id(entry, products),
                fetched_at=now,
            )
        )


def sync_popularity_rankings(db: Session) -> tuple[int, int]:
    """Refreshes popularity_rank for every product in each category from
    that category's current Rakuten ranking. A product not found in the
    latest ranking has its rank cleared (never left showing a stale "still
    popular" claim from a previous run).

    Returns (products_ranked, categories_fetched) - categories_fetched
    counts only categories whose ranking was actually retrieved, so a
    failing API shows up as "0 of 5" rather than looking like success
    (STEP51: every call was being rejected for a missing accessKey, and the
    old count said all 5 categories were "checked")."""
    ranked_count = 0
    checked = 0
    failures: list[str] = []

    for i, (category, genre_id) in enumerate(CATEGORY_GENRE_IDS.items()):
        if i > 0:
            time.sleep(RAKUTEN_REQUEST_INTERVAL_SECONDS)
        try:
            ranking_items = rakuten.fetch_ranking(genre_id, hits=RANKING_HITS)
        except Exception as exc:  # noqa: BLE001 - keep checking other categories
            crud.create_error_log(db, source="popularity", message=f"{category}: {exc}")
            failures.append(category)
            continue
        checked += 1

        products = list(
            db.execute(select(models.Product).where(models.Product.category == category)).scalars()
        )
        _store_ranking_snapshot(db, category, ranking_items, products)
        for product in products:
            rank = _find_rank(product, ranking_items)
            if rank != product.popularity_rank:
                product.popularity_rank = rank
            if rank is not None:
                product.popularity_updated_at = datetime.datetime.utcnow()
                ranked_count += 1
        db.commit()

    if failures and checked == 0:
        # Nothing was refreshed at all - say so plainly, once, so the daily
        # report / admin logs show "ranking is not updating" instead of five
        # per-category lines that are easy to read past.
        crud.create_error_log(
            db,
            source="popularity",
            message=(
                f"楽天の人気ランキングを1カテゴリも取得できませんでした（{len(failures)}カテゴリ失敗）。"
                "サイト上の人気ランキングは更新されていません。RAKUTEN_APP_ID / RAKUTEN_ACCESS_KEY と楽天側のアプリ設定を確認してください。"
            ),
        )
    return ranked_count, checked


def ranking_snapshot(db: Session, limit: int) -> list[dict]:
    """Every category's stored Rakuten ranking (top `limit`), newest-only:
    a category whose snapshot is older than RANKING_MAX_AGE_DAYS is left
    out rather than shown as today's ranking."""
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=RANKING_MAX_AGE_DAYS)
    groups = []
    for category in CATEGORY_GENRE_IDS:
        rows = list(
            db.execute(
                select(models.RakutenRankingEntry)
                .where(models.RakutenRankingEntry.category == category, models.RakutenRankingEntry.fetched_at >= cutoff)
                .order_by(models.RakutenRankingEntry.rank)
                .limit(limit)
            ).scalars()
        )
        if not rows:
            continue
        product_ids = {r.matched_product_id for r in rows if r.matched_product_id}
        products = (
            {p.id: p for p in db.execute(select(models.Product).where(models.Product.id.in_(product_ids))).scalars()}
            if product_ids
            else {}
        )
        entries = []
        for r in rows:
            product = products.get(r.matched_product_id) if r.matched_product_id else None
            if product is not None and product.pending_review:
                product = None  # never link to an unpublished product
            entries.append(
                {
                    "rank": r.rank,
                    "name": r.display_name,
                    "brand": r.brand,
                    "price": r.price,
                    "url": r.affiliate_url or r.item_url,
                    "image_url": r.image_url,
                    "shop_name": r.shop_name,
                    "review_count": r.review_count,
                    "review_average": r.review_average,
                    "product_slug": product.slug if product else None,
                    "product_buy_score": product.buy_score if product else None,
                }
            )
        groups.append({"category": category, "fetched_at": max(r.fetched_at for r in rows), "entries": entries})
    return groups
