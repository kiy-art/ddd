"""STEP68: what searchers who see a product page in Google actually want,
read from that page's real Search Console queries - so the page's <title>
can lead with the matching phrase.

Rule-based and free (no Claude call). The result is only ever one of a
fixed set of intent keys; the frontend (app/products/[slug]/page.tsx,
SEO_TITLE_PHRASES) maps each key to a fixed phrase. Every phrase names
something the product page really has - price comparison across shops,
buy-timing score and price forecast, the spec table - so a retitle can
never promise content that isn't there. Queries asking for things the
page doesn't offer (used items, reviews) are never turned into a title.
"""

import re

# key -> words that signal that intent in a Japanese golf-shopping query.
# Checked in this order - the specific intents first, so "G440 価格推移"
# reads as timing, not as a plain price query - and ties go to the first.
INTENT_PATTERNS: dict[str, re.Pattern] = {
    "timing": re.compile(r"買い時|いつ|推移|値下が|値下げ|下がる|下落|型落ち|モデルチェンジ|新作|発売日"),
    "spec": re.compile(r"スペック|ロフト|ライ角|シャフト|重さ|重量|長さ|フレックス|比較|違い|vs", re.IGNORECASE),
    "price": re.compile(r"最安|安い|激安|価格|値段|相場|セール|値引|割引|楽天|yahoo|ヤフー|amazon|アマゾン", re.IGNORECASE),
}

# The page has none of these - such a query is never a reason to retitle.
UNSERVED_PATTERN = re.compile(r"中古|レビュー|口コミ|評判|評価|試打|ブログ|知恵袋", re.IGNORECASE)

DEFAULT_INTENT = "price"
VALID_INTENTS = frozenset(INTENT_PATTERNS)

# A title change needs a clear signal: the winning intent must carry at
# least this share of the page's (served) query impressions, from at
# least this many impressions in total.
MIN_INTENT_SHARE = 0.4
MIN_TOTAL_IMPRESSIONS = 20


def classify_query(query: str) -> str | None:
    if UNSERVED_PATTERN.search(query):
        return None
    for intent, pattern in INTENT_PATTERNS.items():
        if pattern.search(query):
            return intent
    return None


def dominant_intent(queries: list[dict]) -> tuple[str | None, dict[str, int]]:
    """(intent, impressions per intent). queries are Search Console rows
    ({"query", "impressions", ...}); intent is None when no intent clearly
    leads (see MIN_INTENT_SHARE / MIN_TOTAL_IMPRESSIONS)."""
    totals: dict[str, int] = {}
    served_total = 0
    for row in queries:
        text = str(row.get("query") or "")
        impressions = int(row.get("impressions") or 0)
        if not text or impressions <= 0 or UNSERVED_PATTERN.search(text):
            continue
        served_total += impressions
        intent = classify_query(text)
        if intent:
            totals[intent] = totals.get(intent, 0) + impressions
    if not totals or served_total < MIN_TOTAL_IMPRESSIONS:
        return None, totals
    order = list(INTENT_PATTERNS)
    best = max(totals, key=lambda k: (totals[k], -order.index(k)))
    if totals[best] / served_total < MIN_INTENT_SHARE:
        return None, totals
    return best, totals
