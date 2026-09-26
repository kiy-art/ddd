"""STEP52 "AI厳選・高コスパ消耗品" corner: picks 3-6 consumables for right now.

Rule-based and free (no Claude call), like every other "AI" decision on the
site (analysis.py, content_optimizer.py): the selection only ever quotes
real, stored numbers.

What a "〇% OFF" is measured against (景品表示法 - 二重価格表示):
  1. the maker's list price (msrp), only where it was actually researched
     and entered - labeled "メーカー希望小売価格";
  2. otherwise the median of PAR.'s own recorded prices over the last 30
     days (needs >= MIN_REFERENCE_POINTS records spanning >= 7 days) -
     labeled "直近30日の中央値".
Never a made-up "通常価格". No reference -> no discount badge; the item can
still be picked for the season, just without a "% OFF" claim.

Sale events are only ever the ones the owner entered in
CONSUMABLE_SALE_EVENTS (real dates from each shop's own announcement) -
this module never guesses that a shop is "having a sale".
"""

import dataclasses
import datetime
import json
import re
import statistics
import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import consumables_catalog, crud, image_urls, models, pipeline, rakuten
from app.config import get_settings

PICK_MIN = 3
PICK_MAX = 6
MAX_PER_KIND = 2
MIN_DISCOUNT_BADGE_PCT = 3  # below this a "% OFF" is noise, not a deal
REFERENCE_WINDOW_DAYS = 30
MIN_REFERENCE_POINTS = 5
MIN_REFERENCE_SPAN_DAYS = 7
PRICE_FRESH_DAYS = 7  # a price older than this isn't shown as "now"

# Japanese golf seasons (month, day) start dates, in calendar order.
SEASONS = {
    "spring": "春（シーズンイン）",
    "rainy": "梅雨",
    "summer": "夏",
    "autumn": "秋（ベストシーズン）",
    "winter": "冬",
}
_SEASON_STARTS = [((3, 1), "spring"), ((6, 1), "rainy"), ((7, 16), "summer"), ((9, 11), "autumn"), ((12, 1), "winter")]

KIND_LABELS = {"ball": "ボール", "tee": "ティー", "glove": "グローブ", "care": "ケア用品"}

# Editorial "AI注目" tags per (season, kind): situational, never a
# superlative or an efficacy claim ("最強", "必ず〜" are banned by
# marketing_playbook for the same reason).
_SEASON_TAGS = {
    ("rainy", "glove"): "梅雨どきの替えグローブに",
    ("rainy", "care"): "雨上がりのお手入れに",
    ("summer", "glove"): "汗ばむ季節の替えグローブに",
    ("summer", "care"): "汗・汚れのケアに",
    ("winter", "glove"): "寒い日のラウンドに",
    ("spring", "ball"): "シーズンイン前の補充に",
    ("spring", "tee"): "シーズンイン前の補充に",
    ("spring", "glove"): "シーズンイン前の新調に",
    ("autumn", "ball"): "ラウンドが増える季節の買い足しに",
    ("autumn", "tee"): "ラウンドが増える季節の買い足しに",
}
_KIND_DEFAULT_TAGS = {"ball": "定番の買い足しに", "tee": "定番の買い足しに", "glove": "替えの1枚に", "care": "道具のお手入れに"}


def season_for(day: datetime.date) -> str:
    key = "winter"  # Jan-Feb belong to the winter that started in December
    for (month, dom), season in _SEASON_STARTS:
        if (day.month, day.day) >= (month, dom):
            key = season
    return key


@dataclasses.dataclass
class SaleEvent:
    name: str
    shop: str | None
    start: datetime.date
    end: datetime.date


def active_sale_events(day: datetime.date, raw: str | None = None) -> list[SaleEvent]:
    """Only events the owner entered (CONSUMABLE_SALE_EVENTS), and only on
    the dates they cover. A malformed entry is ignored, never guessed at."""
    raw = get_settings().consumable_sale_events if raw is None else raw
    if not raw or not raw.strip():
        return []
    try:
        entries = json.loads(raw)
    except ValueError:
        return []
    events = []
    for entry in entries if isinstance(entries, list) else []:
        try:
            event = SaleEvent(
                name=str(entry["name"]).strip(),
                shop=(str(entry["shop"]).strip().lower() or None) if entry.get("shop") else None,
                start=datetime.date.fromisoformat(entry["start"]),
                end=datetime.date.fromisoformat(entry["end"]),
            )
        except (KeyError, TypeError, ValueError):
            continue
        if event.name and event.start <= day <= event.end:
            events.append(event)
    return events


@dataclasses.dataclass
class Reference:
    price: int
    basis: str  # "msrp" | "median30"
    label: str


def reference_price(
    current: int | None, msrp: int | None, history: list[tuple[int, datetime.datetime]], now: datetime.datetime
) -> Reference | None:
    """The real price a discount is measured against, or None."""
    if current is None:
        return None
    if msrp and msrp > current:
        return Reference(msrp, "msrp", "メーカー希望小売価格")
    cutoff = now - datetime.timedelta(days=REFERENCE_WINDOW_DAYS)
    window = [(p, t) for p, t in history if t >= cutoff]
    if len(window) >= MIN_REFERENCE_POINTS:
        span = (max(t for _, t in window) - min(t for _, t in window)).days
        if span >= MIN_REFERENCE_SPAN_DAYS:
            median = int(round(statistics.median(p for p, _ in window)))
            if median > current:
                return Reference(median, "median30", "直近30日の中央値")
    return None


@dataclasses.dataclass
class Pick:
    key: str
    kind: str
    brand: str
    name: str
    current_price: int
    reference: Reference | None
    discount_percent: int | None
    savings_yen: int | None
    image_url: str | None
    rakuten_url: str | None
    amazon_query: str
    product_slug: str | None
    product_id: int | None
    season_match: bool
    price_updated_at: datetime.datetime | None
    ai_tag: str = ""
    micro_copy: str = ""
    discount_badge: str | None = None
    savings_text: str | None = None
    score: float = 0.0


def _discount(current: int, ref: Reference | None) -> tuple[int | None, int | None]:
    if ref is None:
        return None, None
    pct = int((ref.price - current) / ref.price * 100)  # floor: never round a discount up
    if pct < MIN_DISCOUNT_BADGE_PCT:
        return None, None
    return pct, ref.price - current


def _candidates(db: Session, season: str, now: datetime.datetime, exclude_product_id: int | None) -> list[Pick]:
    fresh_cutoff = now - datetime.timedelta(days=PRICE_FRESH_DAYS)
    picks: list[Pick] = []

    items = db.execute(select(models.ConsumableItem).where(models.ConsumableItem.active.is_(True))).scalars().all()
    for item in items:
        if item.current_price is None or item.price_updated_at is None or item.price_updated_at < fresh_cutoff:
            continue
        history = [(h.price, h.recorded_at) for h in item.price_history]
        ref = reference_price(item.current_price, item.msrp, history, now)
        pct, savings = _discount(item.current_price, ref)
        picks.append(
            Pick(
                key=f"c-{item.id}",
                kind=item.kind,
                brand=item.brand,
                name=item.name,
                current_price=item.current_price,
                reference=ref if pct is not None else None,
                discount_percent=pct,
                savings_yen=savings,
                image_url=image_urls.normalize_image_url(item.image_url),
                rakuten_url=item.rakuten_url,
                amazon_query=f"{item.brand} {item.name}",
                product_slug=None,
                product_id=None,
                season_match=season in (item.seasons or "").split(","),
                price_updated_at=item.price_updated_at,
            )
        )

    # Golf balls already tracked as catalog products (researched msrp + real
    # daily price history) join the pool as the "ball" consumable.
    balls = db.execute(
        select(models.Product).where(
            models.Product.category == "ball",
            models.Product.pending_review.is_(False),
            models.Product.current_price.is_not(None),
        )
    ).scalars().all()
    for product in balls:
        if product.id == exclude_product_id:
            continue
        history = [(h.price, h.recorded_at) for h in product.price_history]
        last_recorded = max((t for _, t in history), default=None)
        if last_recorded is None or last_recorded < fresh_cutoff:
            continue
        ref = reference_price(product.current_price, product.msrp, history, now)
        pct, savings = _discount(product.current_price, ref)
        picks.append(
            Pick(
                key=f"p-{product.id}",
                kind="ball",
                brand=product.brand,
                name=product.name,
                current_price=product.current_price,
                reference=ref if pct is not None else None,
                discount_percent=pct,
                savings_yen=savings,
                image_url=image_urls.normalize_image_url(product.image_url),
                rakuten_url=product.affiliate_url if product.affiliate_url and "rakuten" in product.affiliate_url else None,
                amazon_query=f"{product.brand} {product.name}",
                product_slug=product.slug,
                product_id=product.id,
                season_match=season in ("spring", "autumn"),
                price_updated_at=last_recorded,
            )
        )
    return picks


def _score(pick: Pick, events: list[SaleEvent]) -> float:
    score = float(min(pick.discount_percent or 0, 50))
    if pick.season_match:
        score += 15
    if pick.rakuten_url and any(e.shop in (None, "rakuten") for e in events):
        score += 8
    return score


def _decorate(pick: Pick, season: str, events: list[SaleEvent]) -> None:
    rakuten_event = next((e for e in events if e.shop in (None, "rakuten")), None)
    if pick.discount_percent is not None and pick.reference is not None and pick.savings_yen is not None:
        pick.discount_badge = f"🔥 {pick.discount_percent}% OFF"
        pick.savings_text = f"{pick.reference.label}より{pick.savings_yen:,}円安い"

    if rakuten_event and pick.rakuten_url:
        pick.ai_tag = f"{rakuten_event.name}期間中"
    elif pick.season_match:
        pick.ai_tag = _SEASON_TAGS.get((season, pick.kind), _KIND_DEFAULT_TAGS.get(pick.kind, "定番の買い足しに"))
    else:
        pick.ai_tag = _KIND_DEFAULT_TAGS.get(pick.kind, "定番の買い足しに")

    parts = []
    # The card already shows savings_text on its own line - the copy says
    # what the comparison means instead of repeating the number.
    if pick.savings_text and pick.reference is not None and pick.reference.basis == "msrp":
        parts.append("メーカー希望小売価格より安く買える水準です。")
    elif pick.savings_text:
        parts.append("PAR.の直近30日の記録と比べて値下がりしているタイミングです。")
    else:
        parts.append("PAR.が毎日記録している現在価格です。")
    if pick.season_match:
        parts.append(f"{SEASONS[season]}の今、{KIND_LABELS.get(pick.kind, '消耗品')}の買い足し候補に選びました。")
    pick.micro_copy = "".join(parts)


def select_picks(
    db: Session,
    today: datetime.date | None = None,
    now: datetime.datetime | None = None,
    exclude_product_id: int | None = None,
    limit: int = PICK_MAX,
) -> tuple[str, list[SaleEvent], list[Pick]]:
    """(season, active_events, picks). picks is empty when fewer than
    PICK_MIN real, fresh candidates exist - a half-empty corner isn't shown."""
    now = now or datetime.datetime.utcnow()
    today = today or (now + datetime.timedelta(hours=9)).date()  # JST
    season = season_for(today)
    events = active_sale_events(today)
    limit = max(PICK_MIN, min(limit, PICK_MAX))

    pool = _candidates(db, season, now, exclude_product_id)
    for pick in pool:
        pick.score = _score(pick, events)
    pool.sort(key=lambda p: (p.score, p.discount_percent or 0, -p.current_price), reverse=True)

    chosen: list[Pick] = []
    per_kind: dict[str, int] = {}
    for pick in pool:  # first pass: variety - at most MAX_PER_KIND of a kind
        if len(chosen) >= limit:
            break
        if per_kind.get(pick.kind, 0) < MAX_PER_KIND:
            chosen.append(pick)
            per_kind[pick.kind] = per_kind.get(pick.kind, 0) + 1
    for pick in pool:  # then fill any remaining slots by score
        if len(chosen) >= limit:
            break
        if pick not in chosen:
            chosen.append(pick)

    if len(chosen) < PICK_MIN:
        return season, events, []
    for pick in chosen:
        _decorate(pick, season, events)
    return season, events, chosen


# --- daily price refresh ------------------------------------------------------


def _normalize(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


def listing_matches_tokens(item_name: str, match_tokens: str) -> bool:
    name = _normalize(item_name)
    for group in (g for g in match_tokens.split(",") if g.strip()):
        if not any(_normalize(alt) in name for alt in group.split("|") if alt.strip()):
            return False
    return True


def seed_catalog(db: Session) -> int:
    """Inserts catalog items whose slug doesn't exist yet. Never overwrites
    an existing row (its prices, history and any admin-set msrp)."""
    existing = set(db.execute(select(models.ConsumableItem.slug)).scalars().all())
    added = 0
    for entry in consumables_catalog.CONSUMABLES:
        if entry["slug"] in existing:
            continue
        db.add(models.ConsumableItem(**entry, active=True))
        added += 1
    if added:
        db.commit()
    return added


def refresh_consumable_prices(db: Session) -> tuple[int, int]:
    """Daily: looks each item up on Rakuten and records the price - only
    from a listing that names this item (match_tokens) and passes the same
    accessory / non-retail / plausibility checks as product prices.
    Returns (updated, skipped)."""
    seed_catalog(db)
    items = db.execute(select(models.ConsumableItem).where(models.ConsumableItem.active.is_(True))).scalars().all()
    updated = skipped = 0
    for i, item in enumerate(items):
        if i > 0:
            time.sleep(pipeline.RAKUTEN_REQUEST_INTERVAL_SECONDS)
        try:
            result = rakuten.search_lowest_price(item.search_keyword)
            reason = None
            if result is None:
                reason = "楽天市場で該当商品が見つかりませんでした"
            elif pipeline._looks_like_accessory(result.item_name) or pipeline._looks_like_non_retail_listing(result.item_name):
                reason = f"「{result.item_name}」は通常の新品販売ではない可能性があります"
            elif not listing_matches_tokens(result.item_name, item.match_tokens):
                reason = f"「{result.item_name}」はこの商品名と一致しません"
            elif item.current_price and not (
                pipeline.PRICE_SANITY_MIN_RATIO <= result.price / item.current_price <= pipeline.PRICE_SANITY_MAX_RATIO
            ):
                reason = f"¥{result.price:,} が前回価格 ¥{item.current_price:,} と大きく乖離しています"
            if reason:
                crud.create_error_log(
                    db, source="consumables", level="info", message=f"{item.brand} {item.name}: {reason}（スキップ）"
                )
                skipped += 1
                continue

            now = datetime.datetime.utcnow()
            item.current_price = result.price
            item.price_updated_at = now
            item.rakuten_url = rakuten.to_affiliate_url(result.item_url) or result.item_url
            new_image = image_urls.normalize_image_url(result.image_url)
            if new_image and image_urls.needs_image(item.image_url):
                item.image_url = new_image
            db.add(models.ConsumablePriceHistory(item_id=item.id, price=result.price, recorded_at=now))
            db.commit()
            updated += 1
        except Exception as exc:  # noqa: BLE001 - one item failing must not stop the batch
            db.rollback()
            crud.create_error_log(db, source="consumables", message=f"{item.brand} {item.name}: {exc}")
            skipped += 1
    return updated, skipped
