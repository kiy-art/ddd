"""Posts the day's best deal(s) to X (Twitter).

Free-tier X API v2 write access only works with OAuth 1.0a user-context
credentials (App-only Bearer auth cannot post) - so requests are signed by
hand (HMAC-SHA1) rather than pulling in a dependency, matching this
codebase's existing direct-httpx style (see rakuten.py/yahoo.py/email.py).
A no-op (posts nothing, no error) whenever the four X_* env vars aren't all
set, the same pattern already used for YAHOO_CLIENT_ID/RESEND_API_KEY.

Product selection and tweet wording only ever use real, already-computed
facts (current_price/msrp/buy_score/buy_signal_score) - Claude is given
those facts and nothing else, and is never allowed to write the URL itself
(that's built from the real slug in code) - the same "AI never invents a
number" rule the rest of the site follows (see app/ai.py).
"""

import base64
import hashlib
import hmac
import json
import secrets
import time
import urllib.parse

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import crud, models
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

SYSTEM_PROMPT = """あなたはゴルフ用品価格比較サイト「PAR.」の公式X(Twitter)アカウント運用担当です。
与えられた事実（商品名・価格・割引率など）のみを根拠に、X投稿用の短い紹介文を1件作成してください。

厳守事項:
- 与えられていない価格・割引率・在庫状況を絶対に創作しない。
- 誇大広告や煽り文句（「今だけ」「絶対お得」等）は使わず、事実ベースで、かつ興味を引く文体にする。
- 日本語で書き、絵文字は0〜2個まで。
- ハッシュタグを2〜3個含める（#ゴルフ #ゴルフクラブ 等、内容に合ったもの）。
- URLは書かない（システム側で別途、投稿の末尾に付与する）。
- 本文全体を90文字以内（日本語の文字数）に収める。
- 出力は必ず次のJSON形式のみ: {"text": "..."}
"""


class XNotConfigured(Exception):
    pass


class XPostError(Exception):
    pass


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
        raise XPostError(f"X API {response.status_code}: {response.text[:500]}")
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


def _truncate_for_x(body: str) -> str:
    budget = X_MAX_WEIGHTED_LENGTH - 1 - X_URL_WEIGHTED_LENGTH  # -1 for the newline before the URL
    if _x_weighted_length(body) <= budget:
        return body
    # Reserve room for the "…" itself (weight 2) before trimming, so the
    # final result - body plus ellipsis - actually stays within budget.
    trim_budget = budget - _x_weighted_length("…")
    while body and _x_weighted_length(body) > trim_budget:
        body = body[:-1]
    return body.rstrip() + "…"


def _product_facts(product: models.Product) -> dict:
    discount_percent = None
    if product.msrp and product.current_price is not None:
        discount_percent = round((product.current_price - product.msrp) / product.msrp * 100, 1)
    return {
        "name": product.name,
        "brand": product.brand,
        "current_price_jpy": product.current_price,
        "msrp_jpy": product.msrp,
        "discount_percent_vs_msrp": discount_percent,
        "price_change_percent_vs_30d_avg": product.price_change_percent,
        "buy_score": product.buy_score,
    }


def _generate_tweet_body_ai(products: list[models.Product]) -> str:
    import anthropic

    settings = get_settings()
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    facts = [_product_facts(p) for p in products]
    message = client.messages.create(
        model=settings.claude_model,
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": "以下の事実だけを根拠にJSONを生成してください:\n" + json.dumps(facts, ensure_ascii=False),
            }
        ],
    )
    text = "".join(block.text for block in message.content if block.type == "text").strip()
    if text.startswith("```"):
        text = text.strip("`").split("\n", 1)[-1]
    data = json.loads(text)
    return str(data["text"])


def _generate_tweet_body_rule_based(products: list[models.Product]) -> str:
    lines = ["本日のお買い得情報"]
    for p in products:
        price = f"¥{p.current_price:,}" if p.current_price is not None else "価格情報なし"
        facts = _product_facts(p)
        if facts["discount_percent_vs_msrp"] is not None:
            lines.append(f"{p.brand} {p.name} が{price}（定価より{facts['discount_percent_vs_msrp']}%）")
        else:
            lines.append(f"{p.brand} {p.name} が{price}")
    lines.append("#ゴルフ #ゴルフクラブ")
    return "\n".join(lines)


def _build_tweet_text(db: Session, products: list[models.Product]) -> str:
    settings = get_settings()

    if len(products) == 1:
        url = f"{settings.site_url}/products/{products[0].slug}"
    else:
        # Multiple picks: link to the shared category page rather than
        # arbitrarily picking one product's own URL.
        url = f"{settings.site_url}/category/{products[0].category}"

    body: str | None = None
    if settings.anthropic_api_key:
        try:
            body = _generate_tweet_body_ai(products)
        except Exception as exc:  # noqa: BLE001 - fall back to rule-based wording
            crud.create_error_log(db, source="x_post", level="warning", message=f"AI tweet generation failed, using rule-based wording: {exc}")
            body = None
    if body is None:
        body = _generate_tweet_body_rule_based(products)

    body = _truncate_for_x(body)
    return f"{body}\n{url}"


def post_daily_deals(db: Session) -> tuple[int, int]:
    """Posts one tweet featuring today's best deal(s). A no-op (returns
    (0, 0)) when X credentials aren't configured or no product qualifies
    today - neither is an error. Returns (posts_sent, posts_skipped)."""
    settings = get_settings()
    if not (settings.x_api_key and settings.x_api_secret and settings.x_access_token and settings.x_access_token_secret):
        return 0, 0

    products = select_deals_of_the_day(db, count=2)
    if not products:
        return 0, 0  # nothing worth posting today - not an error

    text = _build_tweet_text(db, products)

    try:
        tweet_id = post_tweet(text)
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
