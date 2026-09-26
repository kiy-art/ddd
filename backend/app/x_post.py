"""Posts the day's best deal(s) to X (Twitter).

Free-tier X API v2 write access only works with OAuth 1.0a user-context
credentials (App-only Bearer auth cannot post) - so requests are signed by
hand (HMAC-SHA1) rather than pulling in a dependency, matching this
codebase's existing direct-httpx style (see rakuten.py/yahoo.py/email.py).
A no-op (posts nothing, no error) whenever the four X_* env vars aren't all
set, the same pattern already used for YAHOO_CLIENT_ID/RESEND_API_KEY.

Product selection and wording only ever use real, already-computed facts
(current_price/msrp/lowest_price/buy_signal_score/popularity_rank). The
post is built by a deterministic template (STEP45) rather than Claude: a
fixed hook -> product -> price -> CTA -> hashtags structure that's been
designed for SNS click-through, where every emotive hook ("ほぼ半額",
"過去14日間の最安値", "楽天ドライバーランキング3位") is only emitted when the
stored numbers make it literally true, and the result is re-checked by
marketing_playbook.validate_copy (景品表示法) before it's used. Zero API
cost, and the same input always gives the same, reviewable text.
"""

import base64
import dataclasses
import datetime
import hashlib
import hmac
import re
import secrets
import time
import urllib.parse

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import crud, marketing_playbook, models
from app.config import get_settings

POST_URL = "https://api.x.com/2/tweets"

# Reuses the same "enough real price history to trust buy_score" bar the
# rest of the site applies (crud.RELIABLE_TREND_MIN_HISTORY_DAYS /
# frontend's THIN_DATA_DAYS) - never tweets a strong_buy/buy call that's
# actually resting on a couple of noisy data points.
RELIABLE_BUY_SCORES = {"strong_buy", "buy"}

# X's own limit is 280 "weighted" characters (NFC-normalized, most non-Latin
# scripts including Japanese count as 2 toward that total) - this is a
# conservative approximation of that weighting, good enough to decide when
# to truncate, not an exact reimplementation of X's algorithm.
X_MAX_WEIGHTED_LENGTH = 280
# Every link X wraps to a t.co redirect counts as exactly this many
# characters against the 280 limit, regardless of the real URL's length.
X_URL_WEIGHTED_LENGTH = 23

CATEGORY_LABELS = {"driver": "ドライバー", "iron": "アイアン", "wedge": "ウェッジ", "putter": "パター", "ball": "ゴルフボール"}
CATEGORY_HASHTAGS = {"driver": "#ドライバー", "iron": "#アイアン", "wedge": "#ウェッジ", "putter": "#パター", "ball": "#ゴルフボール"}

# A Rakuten bestseller rank older than this isn't "now" any more - not
# worth quoting as a live fact in a post.
POPULARITY_MAX_AGE_DAYS = 3
# Only a top-N rank is a hook worth leading with.
POPULARITY_HOOK_MAX_RANK = 30
# Minimum real history before "過去N日間の最安値" / a 30-day-average
# comparison is a claim this post will make - the same bar the rest of the
# site uses (crud.RELIABLE_TREND_MIN_HISTORY_DAYS, frontend THIN_DATA_DAYS,
# content_rewriter._is_at_recorded_lowest).
MIN_HISTORY_DAYS_FOR_TREND_CLAIMS = 7
# price_change_percent vs the 30-day average needs to be at least this
# negative to be called out as a drop.
AVERAGE_DROP_HOOK_PCT = -5.0

CTA_LINE = "相場推移と取扱店舗はここからチェック👇"

# Same wording as the site (frontend lib/buySignal.ts VERDICTS).
VERDICT_LABELS = {"strong_buy": "今が買い時", "buy": "買い時", "neutral": "様子見", "not_buy": "待つのが無難"}

class XNotConfigured(Exception):
    pass


class XPostError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def _oauth1_authorization_header(method: str, url: str) -> str:
    """Signs a request with OAuth 1.0a (HMAC-SHA1). The tweet-creation
    endpoint takes a JSON body, and per the OAuth 1.0a spec only
    application/x-www-form-urlencoded body params (and query params) are
    part of the signature base string - a JSON body contributes nothing,
    so the only params signed here are the oauth_* ones themselves."""
    settings = get_settings()
    oauth_params = {
        "oauth_consumer_key": settings.x_api_key,
        "oauth_nonce": secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": settings.x_access_token,
        "oauth_version": "1.0",
    }

    def _quote(value: str) -> str:
        return urllib.parse.quote(value, safe="")

    sorted_params = "&".join(f"{_quote(k)}={_quote(v)}" for k, v in sorted(oauth_params.items()))
    base_string = "&".join([method.upper(), _quote(url), _quote(sorted_params)])
    signing_key = f"{_quote(settings.x_api_secret)}&{_quote(settings.x_access_token_secret)}"
    signature = hmac.new(signing_key.encode(), base_string.encode(), hashlib.sha1).digest()
    oauth_params["oauth_signature"] = base64.b64encode(signature).decode()

    header_params = ", ".join(f'{_quote(k)}="{_quote(v)}"' for k, v in sorted(oauth_params.items()))
    return f"OAuth {header_params}"


def post_tweet(text: str, timeout: float = 10.0) -> str:
    """Posts a tweet, returns the created tweet's id. Raises XNotConfigured
    if credentials are missing, XPostError on any API failure."""
    settings = get_settings()
    if not (settings.x_api_key and settings.x_api_secret and settings.x_access_token and settings.x_access_token_secret):
        raise XNotConfigured("X_API_KEY/X_API_SECRET/X_ACCESS_TOKEN/X_ACCESS_TOKEN_SECRET is not fully configured")

    auth_header = _oauth1_authorization_header("POST", POST_URL)
    response = httpx.post(
        POST_URL,
        json={"text": text},
        headers={"Authorization": auth_header, "Content-Type": "application/json"},
        timeout=timeout,
    )
    if response.is_error:
        raise XPostError(f"X API {response.status_code}: {response.text[:500]}", status_code=response.status_code)
    data = response.json()
    return data["data"]["id"]


def select_deals_of_the_day(db: Session, count: int = 2) -> list[models.Product]:
    """Picks today's best deal(s) to feature - real buy_signal_score first
    (only for strong_buy/buy products with enough price history to trust
    it), falling back to MSRP discount (the same fallback tier the
    frontend uses when real trend data is still thin - see
    lib/fallbackScore.ts) when fewer than `count` reliable picks exist.
    Never pads with an unremarkable product: returns fewer than `count`
    (even zero) when nothing genuinely qualifies.

    Deliberately does NOT use crud.list_products(published_only=True):
    that gate excludes every buy_score == "insufficient_data" product from
    list views, which is exactly the population the MSRP-discount fallback
    tier below needs to consider (the same "list view" vs "own page is
    still live" distinction the ANALYZING-display investigation surfaced -
    see docs/ai_company_guidelines.md 3.3). Only pending_review products -
    not yet admin-approved, so not safe to feature - are excluded here."""
    products = list(
        db.execute(select(models.Product).where(models.Product.pending_review.is_(False))).scalars().all()
    )

    reliable = [
        p
        for p in products
        if p.buy_score in RELIABLE_BUY_SCORES
        and p.buy_signal_score is not None
        and p.history_span_days >= crud.RELIABLE_TREND_MIN_HISTORY_DAYS
    ]
    reliable.sort(key=lambda p: p.buy_signal_score, reverse=True)
    picked = reliable[:count]

    if len(picked) < count:
        picked_ids = {p.id for p in picked}
        fallback_candidates = [
            (p, (p.current_price - p.msrp) / p.msrp * 100)
            for p in products
            if p.id not in picked_ids and p.msrp and p.msrp > 0 and p.current_price is not None
        ]
        fallback_candidates.sort(key=lambda pair: pair[1])  # most negative (biggest discount) first
        fallback_candidates = [pair for pair in fallback_candidates if pair[1] < 0]  # never feature a non-discount
        picked += [p for p, _ in fallback_candidates[: count - len(picked)]]

    return picked


def _x_weighted_length(text: str) -> int:
    return sum(2 if ord(ch) > 0x2000 else 1 for ch in text)


@dataclasses.dataclass
class PostFacts:
    """Every number/claim a post may state about one product - computed
    once from stored data so the wording below can't drift from it."""

    savings_yen: int | None  # vs the recorded MSRP, only when actually below it
    savings_percent: int | None  # rounded, for display only
    savings_ratio: float | None  # exact - every threshold ("半額以下" etc.) uses this, never the rounded value
    at_recorded_lowest: bool  # current <= lowest recorded, with >= 7 days of history
    average_drop_percent: float | None  # vs 30-day average, only a real, reliable drop
    buy_signal_score: int | None  # only when resting on enough history
    popularity_rank: int | None  # Rakuten bestseller rank, only when fresh


def _post_facts(product: models.Product) -> PostFacts:
    current = product.current_price
    reliable_history = (product.history_span_days or 0) >= MIN_HISTORY_DAYS_FOR_TREND_CLAIMS

    savings_yen = savings_percent = savings_ratio = None
    if current is not None and product.msrp and product.msrp > current:
        savings_yen = product.msrp - current
        savings_ratio = savings_yen / product.msrp
        savings_percent = round(savings_ratio * 100)

    at_recorded_lowest = bool(
        reliable_history
        and current is not None
        and product.lowest_price is not None
        and current <= product.lowest_price
    )

    average_drop_percent = None
    if (
        reliable_history
        and product.buy_score != "insufficient_data"
        and product.price_change_percent is not None
        and product.price_change_percent <= AVERAGE_DROP_HOOK_PCT
    ):
        average_drop_percent = product.price_change_percent

    buy_signal_score = (
        product.buy_signal_score
        if reliable_history and product.buy_score in RELIABLE_BUY_SCORES and product.buy_signal_score is not None
        else None
    )

    popularity_rank = None
    if product.popularity_rank is not None and product.popularity_updated_at is not None:
        age = datetime.datetime.utcnow() - product.popularity_updated_at
        if age <= datetime.timedelta(days=POPULARITY_MAX_AGE_DAYS):
            popularity_rank = product.popularity_rank

    return PostFacts(
        savings_yen=savings_yen,
        savings_percent=savings_percent,
        savings_ratio=savings_ratio,
        at_recorded_lowest=at_recorded_lowest,
        average_drop_percent=average_drop_percent,
        buy_signal_score=buy_signal_score,
        popularity_rank=popularity_rank,
    )


def _hook(product: models.Product, facts: PostFacts) -> str:
    """The thumb-stopping first line - the single strongest statement that
    is literally true for this product. Same ladder as the share-image
    headline chip (frontend lib/og.tsx productShareFacts), so the post and
    its link card tell one story."""
    label = CATEGORY_LABELS.get(product.category, "ゴルフギア")
    subject = (
        f"楽天ランキング{facts.popularity_rank}位の{label}"
        if facts.popularity_rank is not None and facts.popularity_rank <= POPULARITY_HOOK_MAX_RANK
        else f"注目の{label}"
    )
    # Thresholds on the exact ratio: 49.7% off rounds to "50%" but is not
    # "半額以下" - that rounding gap is exactly a 有利誤認 risk.
    ratio = facts.savings_ratio

    if facts.at_recorded_lowest:
        return f"📉 {subject}が過去{product.history_span_days}日間の最安値に"
    if ratio is not None and ratio >= 0.5:
        return f"😳 {subject}が定価の半額以下に"
    if ratio is not None and ratio >= 0.45:
        return f"😳 {subject}がほぼ半額に"
    if ratio is not None and ratio >= 0.3:
        return f"💥 {subject}が定価から{facts.savings_yen:,}円引き"
    if facts.average_drop_percent is not None:
        return f"📉 {subject}が30日平均より{abs(facts.average_drop_percent):g}%ダウン"
    if facts.savings_yen is not None:
        return f"💰 {subject}が定価より{facts.savings_yen:,}円お得"
    return f"⛳️ 今日の買い時{label}"


def _price_line(product: models.Product, facts: PostFacts) -> str:
    price = f"¥{product.current_price:,}" if product.current_price is not None else "価格情報なし"
    if facts.savings_yen is not None:
        return f"💰 {price}（定価より¥{facts.savings_yen:,}安い／-{facts.savings_percent}%）"
    if facts.average_drop_percent is not None and product.average_price:
        # The hook already states the % - show the real reference price instead.
        return f"💰 {price}（30日平均 ¥{product.average_price:,}）"
    return f"💰 {price}"


def _hashtag(text: str) -> str | None:
    """#TaylorMade, #ゼクシオ - hashtags break on spaces/punctuation, so
    keep only word characters (kana/kanji included)."""
    cleaned = re.sub(r"[^\w]", "", text)
    return f"#{cleaned}" if cleaned and not cleaned.isdigit() else None


def _hashtags(products: list[models.Product]) -> str:
    tags = ["#ゴルフ"]
    for tag in [CATEGORY_HASHTAGS.get(p.category) for p in products] + [
        _hashtag(products[0].brand)
    ]:
        if tag and tag not in tags:
            tags.append(tag)
    return " ".join(tags[:4])


def _shorten(name: str, max_len: int | None) -> str:
    """Trims at a word boundary where possible ("STEALTH 2 PLUS…", not
    "STEALTH 2 PLUS ドライ…")."""
    if max_len is None or len(name) <= max_len:
        return name
    cut = name[: max_len - 1]
    space = cut.rfind(" ")
    if space >= max_len // 2:
        cut = cut[:space]
    return cut.rstrip() + "…"


def _teaser_line(product: models.Product, facts: PostFacts, name_max: int | None = None) -> str:
    name = _shorten(f"{product.brand} {product.name}", name_max)
    if facts.savings_percent is not None:
        return f"➕ {name}も定価より-{facts.savings_percent}%"
    price = f"¥{product.current_price:,}" if product.current_price is not None else ""
    return f"➕ もう1本：{name}（{price}）" if price else f"➕ もう1本：{name}"


def _post_weighted_length(text_without_url: str) -> int:
    # The URL is its own line; X counts it as a fixed 23 regardless of length.
    return _x_weighted_length(text_without_url) + X_URL_WEIGHTED_LENGTH


def _compose(
    lead: models.Product,
    lead_facts: PostFacts,
    others: list[tuple[models.Product, PostFacts]],
    url: str,
    hashtags: str,
    include_signal: bool,
    include_teaser: bool,
    name_max: int | None,
) -> tuple[str, int]:
    name = _shorten(f"{lead.brand} {lead.name}", name_max)

    blocks = [_hook(lead, lead_facts), "", name, _price_line(lead, lead_facts)]
    if include_signal and lead_facts.buy_signal_score is not None:
        # Verdict next to the number (STEP49) - "82/100" alone means nothing.
        verdict = VERDICT_LABELS.get(lead.buy_score)
        blocks.append(
            f"📊 PAR.買い時スコア {lead_facts.buy_signal_score}/100" + (f"（{verdict}）" if verdict else "")
        )
    if include_teaser:
        for product, facts in others:
            blocks += ["", _teaser_line(product, facts, name_max)]
    blocks += ["", CTA_LINE]
    head = "\n".join(blocks)
    tail = hashtags
    text = f"{head}\n{url}\n\n{tail}"
    return text, _post_weighted_length(f"{head}\n\n\n{tail}")


def _generate_post_text(products: list[models.Product], url: str) -> str:
    """Hook -> product -> price -> (signal) -> (runner-up) -> CTA -> URL ->
    hashtags. Richest version that fits X's limit wins; elements are shed
    least-important first (long names, then the runner-up, then the score
    line), never the hook, price or CTA."""
    lead, rest = products[0], products[1:]
    lead_facts = _post_facts(lead)
    others = [(p, _post_facts(p)) for p in rest]
    hashtags = _hashtags(products)

    attempts = [
        dict(include_signal=True, include_teaser=True, name_max=None),
        dict(include_signal=True, include_teaser=True, name_max=30),
        dict(include_signal=True, include_teaser=False, name_max=None),
        dict(include_signal=True, include_teaser=False, name_max=30),
        dict(include_signal=False, include_teaser=False, name_max=30),
    ]
    for kwargs in attempts:
        text, weighted = _compose(lead, lead_facts, others, url, hashtags, **kwargs)
        if weighted <= X_MAX_WEIGHTED_LENGTH:
            return text
    # Pathological names only - keep the structure, hard-trim the name.
    text, _ = _compose(lead, lead_facts, others, url, "#ゴルフ", include_signal=False, include_teaser=False, name_max=12)
    return text


def _allowed_facts(products: list[models.Product]) -> tuple[set[int], set[float], bool]:
    yen: set[int] = set()
    percents: set[float] = set()
    lowest_claim = False
    for product in products:
        facts = _post_facts(product)
        yen |= {v for v in (product.current_price, product.msrp, product.average_price, facts.savings_yen) if v is not None}
        percents |= {float(v) for v in (facts.savings_percent, facts.average_drop_percent) if v is not None}
        if facts.average_drop_percent is not None:
            percents.add(abs(facts.average_drop_percent))
        lowest_claim = lowest_claim or facts.at_recorded_lowest
    return yen, percents, lowest_claim


def _build_tweet_text(db: Session, products: list[models.Product]) -> str:
    settings = get_settings()
    # One post, one link: the lead product's own page, whose share card
    # (frontend app/products/[slug]/opengraph-image.tsx) shows its photo,
    # price and the same hook - the strongest possible link preview. A
    # runner-up is mentioned in the text, not given a competing link.
    url = f"{settings.site_url}/products/{products[0].slug}"
    text = _generate_post_text(products, url)

    allowed_yen, allowed_percents, lowest_claim = _allowed_facts(products)
    try:
        marketing_playbook.validate_copy(
            [text.replace(url, "")], allowed_yen, allowed_percents, allow_lowest_price_claim=lowest_claim
        )
    except marketing_playbook.ContentPolicyViolation as exc:
        # Should be impossible (the template only states computed facts) -
        # if it ever happens, log it and fall back to the plainest version.
        crud.create_error_log(db, source="x_post", level="warning", message=f"X post text failed compliance check: {exc}")
        lead = products[0]
        price = f"¥{lead.current_price:,}" if lead.current_price is not None else ""
        text = f"⛳️ {lead.brand} {lead.name} {price}\n{CTA_LINE}\n{url}\n\n#ゴルフ"
    return text


def build_manual_post_text(db: Session) -> str | None:
    """The same text `post_daily_deals` would tweet if it posted - built
    from the exact same product selection and wording (select_deals_of_the_
    day + _build_tweet_text below) - for a human to copy/paste onto X
    directly. Returns None (never a fabricated placeholder) when nothing
    genuinely qualifies today, same as post_daily_deals itself.

    Used by app/daily_report.py (the morning email) and the admin page's
    "手動投稿用テキストのプレビュー" so both always show exactly what the
    automated poster would have said - one selection/wording path, not two
    that could drift apart."""
    products = select_deals_of_the_day(db, count=2)
    if not products:
        return None
    return _build_tweet_text(db, products)


def post_daily_deals(db: Session) -> tuple[int, int]:
    """Posts one tweet featuring today's best deal(s). A no-op (returns
    (0, 0)) when X credentials aren't configured or no product qualifies
    today - neither is an error. Returns (posts_sent, posts_skipped).

    X's free API tier stopped allowing tweet creation (402 Payment
    Required) - this is a standing, not transient, condition, so it's
    treated as a graceful skip (an info-level log carrying the ready-to-
    paste text, not an "error") rather than a failure the daily batch or
    an admin should be alarmed about. Any other failure (real auth error,
    network issue, etc.) still logs at the normal error level."""
    settings = get_settings()
    if not (settings.x_api_key and settings.x_api_secret and settings.x_access_token and settings.x_access_token_secret):
        return 0, 0

    text = build_manual_post_text(db)
    if text is None:
        return 0, 0  # nothing worth posting today - not an error

    try:
        tweet_id = post_tweet(text)
    except XPostError as exc:
        if exc.status_code == 402:
            crud.create_error_log(
                db,
                source="x_post",
                level="info",
                message=f"X API 402（無料プランでは投稿できません）のため自動投稿をスキップし、手動投稿用テキストを生成・ログ出力完了:\n{text}",
            )
            return 0, 1
        crud.create_error_log(db, source="x_post", message=f"X post failed: {exc}\n投稿予定だった本文:\n{text}")
        return 0, 1
    except Exception as exc:  # noqa: BLE001 - one failed post shouldn't be fatal to the caller
        crud.create_error_log(db, source="x_post", message=f"X post failed: {exc}\n投稿予定だった本文:\n{text}")
        return 0, 1

    crud.create_error_log(
        db,
        source="x_post",
        level="info",
        message=f"Xに投稿しました（tweet_id={tweet_id}）:\n{text}",
    )
    return 1, 0
