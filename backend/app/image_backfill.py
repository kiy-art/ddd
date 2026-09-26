"""On-demand fill-in of product photos (admin button, STEP48).

The daily price fetch (app/pipeline.py) already fills a missing photo from
the Rakuten/Yahoo listing it matched. This does the same immediately, for
every product the site currently shows as NO IMAGE, instead of waiting for
the next 06:00 run - and additionally finds stored photos that are gone
(the image server answers 404/410 or with a non-image), which the daily
fetch can't see because it never loads the photo itself.

A photo is only ever taken from a listing that passes the exact same
checks the price fetch uses to decide a listing is this product
(_looks_like_accessory / _looks_like_non_retail_listing /
_is_plausible_price) - a head cover's photo on a driver's page would be
worse than NO IMAGE. It never records a price: photos only.
"""

import dataclasses
import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import crud, image_urls, models, pipeline, rakuten, yahoo


@dataclasses.dataclass
class ImageBackfillResult:
    checked: int = 0
    broken_found: int = 0
    filled_from_rakuten: int = 0
    filled_from_yahoo: int = 0
    still_missing: list[str] = dataclasses.field(default_factory=list)
    yahoo_quota_exhausted: bool = False


def _listing_matches(product: models.Product, result) -> bool:
    return (
        result is not None
        and not pipeline._looks_like_accessory(result.item_name)
        and not pipeline._looks_like_non_retail_listing(result.item_name)
        and pipeline._is_plausible_price(product, result.price)
    )


def backfill_product_images(db: Session, verify_existing: bool = True) -> ImageBackfillResult:
    result = ImageBackfillResult()
    products = list(db.execute(select(models.Product).order_by(models.Product.id)).scalars().all())
    use_yahoo = True
    first_api_call = True

    def _pace(interval: float) -> None:
        nonlocal first_api_call
        if not first_api_call:
            time.sleep(interval)
        first_api_call = False

    for product in products:
        result.checked += 1
        needs = image_urls.needs_image(product.image_url)

        if not needs and verify_existing:
            current = image_urls.normalize_image_url(product.image_url)
            if current and image_urls.is_definitely_broken(current):
                result.broken_found += 1
                needs = True

        if not needs:
            # A valid-but-http or oddly spaced value is still stored in its
            # normalized form, so everything downstream sees one shape.
            normalized = image_urls.normalize_image_url(product.image_url)
            if normalized != product.image_url:
                product.image_url = normalized
                db.commit()
            continue

        keyword = f"{product.brand} {product.name}".strip()
        new_image: str | None = None
        source = None
        try:
            _pace(pipeline.RAKUTEN_REQUEST_INTERVAL_SECONDS)
            found = rakuten.search_lowest_price(keyword)
            if _listing_matches(product, found):
                new_image = image_urls.normalize_image_url(found.image_url)
                source = "rakuten"
        except Exception as exc:  # noqa: BLE001 - one lookup failing must not stop the run
            crud.create_error_log(
                db, source="image_backfill", level="warning", product_id=product.id,
                message=f"{product.name}: 楽天での画像検索に失敗しました: {exc}",
            )

        if new_image is None and use_yahoo:
            try:
                _pace(pipeline.YAHOO_REQUEST_INTERVAL_SECONDS)
                found = yahoo.search_lowest_price(keyword)
                if _listing_matches(product, found):
                    new_image = image_urls.normalize_image_url(found.image_url)
                    source = "yahoo"
            except yahoo.YahooQuotaExceeded:
                # Same circuit breaker as the daily Yahoo fetch: the quota is
                # for the whole day, so stop asking for the rest of this run.
                use_yahoo = False
                result.yahoo_quota_exhausted = True
            except Exception as exc:  # noqa: BLE001
                crud.create_error_log(
                    db, source="image_backfill", level="warning", product_id=product.id,
                    message=f"{product.name}: Yahoo!での画像検索に失敗しました: {exc}",
                )

        if new_image is not None:
            product.image_url = new_image
            if source == "rakuten":
                result.filled_from_rakuten += 1
            else:
                result.filled_from_yahoo += 1
        else:
            # Nothing trustworthy found: store None rather than a broken /
            # placeholder value, so the page's structured data falls back to
            # the product's own share card instead of a dead URL.
            product.image_url = None
            result.still_missing.append(product.name)
        db.commit()

    if result.filled_from_rakuten or result.filled_from_yahoo or result.broken_found:
        crud.create_error_log(
            db, source="image_backfill", level="info",
            message=(
                f"商品画像の補完: 確認{result.checked}件 / リンク切れ{result.broken_found}件 / "
                f"楽天から{result.filled_from_rakuten}件・Yahoo!から{result.filled_from_yahoo}件を補完 / "
                f"見つからず{len(result.still_missing)}件"
            ),
        )
    return result


def clear_broken_images(db: Session) -> int:
    """Daily-batch step (runs just before the Rakuten price fetch): clears
    stored photos that are definitely gone or were never usable, so that
    same run's price fetch - which fills any photo the site can't show -
    replaces them from the listing it matches. Makes no Rakuten/Yahoo API
    calls of its own (the Yahoo quota is already tight, STEP40): it only
    loads the stored photo URLs themselves. Returns how many were cleared."""
    cleared = 0
    for product in db.execute(select(models.Product).where(models.Product.image_url.is_not(None))).scalars():
        current = image_urls.normalize_image_url(product.image_url)
        if current is None or image_urls.is_definitely_broken(current):
            product.image_url = None
            cleared += 1
        elif current != product.image_url:
            product.image_url = current
    db.commit()
    return cleared
