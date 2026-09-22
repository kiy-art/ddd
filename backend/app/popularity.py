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

from app import crud, models, rakuten
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


def sync_popularity_rankings(db: Session) -> tuple[int, int]:
    """Refreshes popularity_rank for every product in each category from
    that category's current Rakuten ranking. A product not found in the
    latest ranking has its rank cleared (never left showing a stale "still
    popular" claim from a previous run).

    Returns (products_ranked, categories_checked)."""
    ranked_count = 0
    checked = 0

    for i, (category, genre_id) in enumerate(CATEGORY_GENRE_IDS.items()):
        if i > 0:
            time.sleep(RAKUTEN_REQUEST_INTERVAL_SECONDS)
        checked += 1
        try:
            ranking_items = rakuten.fetch_ranking(genre_id, hits=RANKING_HITS)
        except Exception as exc:  # noqa: BLE001 - keep checking other categories
            crud.create_error_log(db, source="popularity", message=f"{category}: {exc}")
            continue

        products = list(
            db.execute(select(models.Product).where(models.Product.category == category)).scalars()
        )
        for product in products:
            rank = _find_rank(product, ranking_items)
            if rank != product.popularity_rank:
                product.popularity_rank = rank
            if rank is not None:
                product.popularity_updated_at = datetime.datetime.utcnow()
                ranked_count += 1
        db.commit()

    return ranked_count, checked
