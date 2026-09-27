"""STEP61: pulls a product's spec table (loft, shaft, length, ...) out of
the shop's own item description that Rakuten's search API returns
(itemCaption) - so product pages and the compare table can show real
specs instead of price alone.

These are the SELLER'S stated specs, shown as such ("販売ページ記載").
Nothing is guessed: a spec is only kept when a known label is followed by
a value in the caption text, and the value is kept as written (trimmed),
e.g. "9°/10.5°" for a driver sold in two lofts. Unknown formats simply
yield nothing.
"""

import re

# (key, display label, label patterns) - order = display order.
SPEC_FIELDS: list[tuple[str, str, str]] = [
    ("loft", "ロフト角", r"ロフト角?|LOFT"),
    ("lie", "ライ角", r"ライ角"),
    ("bounce", "バンス角", r"バウ?ンス角?"),
    ("head_volume", "ヘッド体積", r"ヘッド体積|体積"),
    ("length", "クラブ長さ", r"クラブ長さ|長さ|レングス"),
    ("weight", "クラブ重量", r"クラブ重量|総重量|重量"),
    ("shaft", "シャフト", r"シャフト(?:名|モデル)?"),
    ("flex", "フレックス", r"フレックス|硬さ|FLEX"),
    ("balance", "バランス", r"バランス"),
    ("set", "番手構成", r"番手構成|セット内容|番手"),
    ("material", "ヘッド素材", r"ヘッド素材|素材|材質"),
    ("construction", "構造", r"構造|ピース"),
    ("cover", "カバー", r"カバー素材|カバー"),
]

# Which specs are meaningful per category (others are ignored even if found:
# a ball listing's "重量" is the ball's, not a club's).
CATEGORY_FIELDS = {
    "driver": ["loft", "lie", "head_volume", "length", "weight", "shaft", "flex", "balance", "material"],
    "iron": ["set", "loft", "lie", "length", "weight", "shaft", "flex", "balance", "material"],
    "wedge": ["loft", "bounce", "lie", "length", "weight", "shaft", "flex", "material"],
    "putter": ["loft", "lie", "length", "weight", "material"],
    "ball": ["construction", "cover"],
}

LABELS = {key: label for key, label, _ in SPEC_FIELDS}

_ANY_LABEL = "|".join(pattern for _, _, pattern in SPEC_FIELDS)
# Several specs on one line ("シャフト：MCI 60 フレックス：R", "構造：4ピース
# カバー：ウレタン"): start a new segment wherever a known label followed
# by ":" (or a bracket) comes after whitespace.
_LABEL_START = re.compile(rf"[\s　]+(?=(?:{_ANY_LABEL})\s*(?:[\(（][^)）]{{0,8}}[\)）])?\s*[:：=＝】])", re.IGNORECASE)


_MAX_VALUE_LEN = 40
_SEPARATORS = re.compile(r"<br\s*/?>|<[^>]+>|[\n\r]|[■◆●◇□▼▲★☆※]|【|】|\[|\]|｜|\|")
_NOISE_VALUE = re.compile(r"送料|ポイント|クーポン|お問い合わせ|ご注文|在庫|納期|注意|http", re.IGNORECASE)


def _segments(caption: str) -> list[str]:
    text = _LABEL_START.sub("\n", caption)
    return [seg.strip() for seg in _SEPARATORS.split(text) if seg and seg.strip()]


def _clean_value(raw: str) -> str | None:
    value = raw.strip(" 　:：=＝-－・/／").strip()
    # stop at the next "label:" in the same run of text
    value = re.split(r"\s{2,}|　{1,}|[、。]|(?<=\S)\s+(?=[^\s:：]{1,8}[:：])", value)[0].strip()
    # ...or at the next known label written without a colon ("10.5 シャフト重量 60g")
    value = re.split(rf"\s+(?=(?:{_ANY_LABEL}))", value, flags=re.IGNORECASE)[0].strip()
    if not value or len(value) > _MAX_VALUE_LEN or _NOISE_VALUE.search(value):
        return None
    if not re.search(r"[0-9０-９A-Za-zァ-ヶー一-龯]", value):
        return None
    return value


def extract_specs(caption: str | None, category: str) -> dict[str, str]:
    """{spec key: value as written}, only for this category's fields."""
    fields = CATEGORY_FIELDS.get(category)
    if not caption or not fields:
        return {}
    wanted = [(key, pattern) for key, _, pattern in SPEC_FIELDS if key in fields]
    specs: dict[str, str] = {}
    segments = _segments(caption)
    for i, seg in enumerate(segments):
        for key, pattern in wanted:
            if key in specs:
                continue
            m = re.match(rf"^(?:{pattern})\s*(?:[\(（][^)）]{{0,8}}[\)）])?\s*[:：=＝]?\s*(.*)$", seg, re.IGNORECASE)
            if not m:
                continue
            rest = m.group(1)
            # "【ロフト角】10.5°" - the value is in the next segment
            if not rest and i + 1 < len(segments):
                rest = segments[i + 1]
            value = _clean_value(rest)
            if value:
                specs[key] = value
            break
    return specs


def merge_specs(existing: dict[str, str] | None, new: dict[str, str]) -> dict[str, str]:
    """Adds only keys the product doesn't have yet - a spec once recorded
    isn't replaced by a different shop's listing wording."""
    merged = dict(existing or {})
    for key, value in new.items():
        merged.setdefault(key, value)
    return merged
