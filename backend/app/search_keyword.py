"""STEP74: build a Rakuten Ichiba search keyword that the API accepts.

Products whose stored name still carries a raw Rakuten listing title (e.g.
"ピン G440K ドライバー ALTA J CB BLUE G440 K 右用") were failing every daily
price fetch with HTTP 400 - 184 products on 2026-10-04, 72% of that week's
error log. Rakuten rejects a keyword when any space-separated token is

  - a single character that is not a kanji: "K", but also a full-width
    "Ｋ" and a lone kana "ス" / "の" (STEP75, below), or
  - made only of symbols ("/", "［", a lone "ー"),

or when the whole keyword is 128 characters or longer. Confirmed against
the production error log: every one of the 184 failures on 2026-10-04
matched, and no passing keyword did.

STEP75 (2026-10-06): STEP74 widened a lone "K" to "Ｋ" to keep the model
letter. The first daily run with it showed Rakuten rejects that too -
all 81 widened keywords failed, while single kanji ("白", "入", "旗") in
passing keywords were accepted. A lone non-kanji character is now
dropped instead. That widens the search, and pipeline.py's price
plausibility check does NOT fully guard it: a product with no reference
price is accepted as-is, and a sibling model of the same series ("G440"
for "G440 K") is priced close enough to pass. So when dropping leaves at
most one word besides the brand, no keyword is returned (the product is
skipped) - and the products affected were snapshotted before the first
run so a wrong match can be traced and undone (docs/meetings/
2026-10-06-keywords-step75.csv, audit 2026-10-06).

`build_search_keyword` keeps a keyword that is already valid exactly as it
was, so the ~400 products that fetch fine today keep matching the same
listings. Only an invalid one is rebuilt, from the rule-based promo
stripping in title_cleaner (never the Claude-based cleaner - no cost).
"""

import re
import unicodedata

from app.brands import BRAND_NAME_SYNONYMS
from app.title_cleaner import strip_promotional_noise

MAX_KEYWORD_CHARS = 128  # Rakuten: must be under this many characters
TARGET_KEYWORD_CHARS = 100  # rebuilt keywords stay well inside the limit

# Separators a listing title uses between parts; splitting on them (and not
# on "-" or "." inside a token) keeps model numbers like FR-3, N.S.PRO, 2.0.
_SPLIT_PATTERN = re.compile(r"[\s　/／｜|・「」『』［］\[\]【】()（）《》≪≫<>＜＞,，、：:●◆★☆＼]+")
_TOKEN_EDGE_CHARS = "-‐~～_"
_SYMBOL_ONLY_EXTRA = set("ー〜～")

def _is_symbol_only(token: str) -> bool:
    return all(unicodedata.category(ch)[0] in "PSZ" or ch in _SYMBOL_ONLY_EXTRA for ch in token)


def _is_kanji(ch: str) -> bool:
    return unicodedata.name(ch, "").startswith("CJK UNIFIED IDEOGRAPH")


def _is_invalid_token(token: str) -> bool:
    return (len(token) == 1 and not _is_kanji(token)) or _is_symbol_only(token)


def _tokens(keyword: str) -> list[str]:
    return [t for t in re.split(r"[ 　]+", keyword) if t]


def is_valid_rakuten_keyword(keyword: str | None) -> bool:
    if not keyword or len(keyword) >= MAX_KEYWORD_CHARS:
        return False
    tokens = _tokens(keyword)
    return bool(tokens) and not any(_is_invalid_token(t) for t in tokens)


def _brand_names(brand: str) -> set[str]:
    names = {brand.lower()}
    names.update(n.lower() for n in BRAND_NAME_SYNONYMS.get(brand, []))
    return names


def build_search_keyword(brand: str | None, name: str | None, max_chars: int = TARGET_KEYWORD_CHARS) -> str | None:
    """The keyword to search Rakuten with, or None when no valid one can be
    made (the caller then skips the API call instead of logging a 400)."""
    brand = (brand or "").strip()
    name = (name or "").strip()
    original = f"{brand} {name}".strip()
    if is_valid_rakuten_keyword(original):
        return original

    cleaned = strip_promotional_noise(name, brand=brand or None) if name else ""
    seen: set[str] = set()
    tokens: list[str] = []
    dropped = False
    for raw in _SPLIT_PATTERN.split(cleaned):
        token = raw.strip(_TOKEN_EDGE_CHARS)
        if not token:
            continue
        if _is_invalid_token(token):
            dropped = dropped or not _is_symbol_only(token)
            continue
        key = unicodedata.normalize("NFKC", token).lower()
        if key in seen:
            continue
        seen.add(key)
        tokens.append(token)

    if brand and not any(unicodedata.normalize("NFKC", t).lower() in _brand_names(brand) for t in tokens):
        tokens.insert(0, brand)

    kept: list[str] = []
    length = 0
    for token in tokens:
        added = len(token) + (1 if kept else 0)
        if length + added > max_chars:
            break
        kept.append(token)
        length += added
    brand_names = _brand_names(brand) if brand else set()
    others = [t for t in kept if unicodedata.normalize("NFKC", t).lower() not in brand_names]
    if not others or (dropped and len(others) < 2):
        return None  # only the brand (in any spelling), or one word, left - far too broad
    keyword = " ".join(kept)
    return keyword if is_valid_rakuten_keyword(keyword) else None
