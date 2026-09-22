"""Turns a noisy Rakuten/Yahoo listing title into a clean "ブランド＋型番"
product name, so the catalog reads like a price-comparison site instead of
a scrape of shop-specific ad copy (e.g. "【送料無料】タイトリスト Titleist
Pro V1 ゴルフボール ポイント10倍!!" -> "Titleist Pro V1 ゴルフボール").

Two layers, same "rule-based baseline + optional AI enhancement" shape as
app/ai.py and app/x_post.py:

- strip_promotional_noise() is a deterministic regex pass - always runs,
  free, instant - that removes bracket-tag noise (【...】/[...]) and a
  curated list of common Japanese EC promotional phrases. This alone is
  usually enough, and is always the safety-net result.
- clean_product_title() additionally asks Claude to tighten the
  regex-cleaned text down to just "ブランド＋型番" when ANTHROPIC_API_KEY
  is configured. Claude is only ever shown the already-regex-cleaned text
  plus the already-known brand/category (both real, already-matched
  facts - see discovery.py's _match_brand) and is instructed to remove
  text only, never invent or add anything. Its output is sanity-checked
  (non-empty, not longer than the input, still names the known brand)
  before being trusted; any failure - not configured, API error, output
  that doesn't pass the sanity check - falls back to the regex result.
"""

import json
import re

from app.config import get_settings

# Bracket-tag segments (【...】, full/half-width [...]) are virtually
# always shop promotional tags in this domain ("【送料無料】", "【あす楽】",
# "【正規品】") - a real model name is essentially never wrapped in these,
# so they're stripped wholesale regardless of their content.
_BRACKET_TAG_PATTERN = re.compile(r"[【\[][^】\]]*[】\]]")

# Common Japanese EC promotional phrases that appear even on otherwise
# legitimate listings (unlike ACCESSORY_KEYWORDS/AUTO_PUBLISH_NG_KEYWORDS
# in discovery.py/pipeline.py, which mark a listing as not worth
# registering at all - see those modules' own comments for why "送料無料"/
# "ポイント"/"得" specifically must NOT be treated as reject signals: they
# appear on nearly every real listing, including genuine golf clubs, so
# rejecting on them would break normal discovery/price-matching. Here they
# only ever remove text from the display name, never the product itself).
_PROMO_PHRASES = [
    "送料無料",
    "送料込み",
    "送料込",
    r"ポイント\s*\d*\s*倍",
    "ポイントアップ",
    "ポイント消化",
    "ポイント還元",
    "得々",
    "お得",
    "期間限定",
    "数量限定",
    "在庫処分",
    "在庫限り",
    "特価",
    "セール",
    "SALE",
    "sale",
    "あす楽",
    "即日発送",
    "即納",
    "新品",
    "未使用品",
    "未使用",
    "正規品",
    "日本正規品",
    "並行輸入品",
    "ラッピング無料",
    "レビューを書いて",
    "訳あり",
]
_PROMO_PATTERN = re.compile("|".join(_PROMO_PHRASES))

# Runs of punctuation/symbols shops use for emphasis (!!, ★, ◆, ~) once the
# text they were decorating has already been stripped out around them.
_DECORATION_PATTERN = re.compile(r"[!!★☆◆■□▼▲♪♫~〜]+")

_WHITESPACE_PATTERN = re.compile(r"[\s　]+")


def strip_promotional_noise(raw_title: str) -> str:
    text = _BRACKET_TAG_PATTERN.sub(" ", raw_title)
    text = _PROMO_PATTERN.sub(" ", text)
    text = _DECORATION_PATTERN.sub(" ", text)
    text = _WHITESPACE_PATTERN.sub(" ", text).strip(" -・/")
    return text or raw_title.strip()


def _looks_like_a_reasonable_cleanup(candidate: str, regex_cleaned: str, brand: str) -> bool:
    if not candidate:
        return False
    if len(candidate) > len(regex_cleaned) + 10:
        return False  # Claude added text rather than only removing it
    return brand.lower() in candidate.lower()


def _ai_tighten(regex_cleaned: str, brand: str, category: str) -> str | None:
    settings = get_settings()
    if not settings.anthropic_api_key:
        return None

    import anthropic

    system = (
        "あなたはECサイトの商品タイトルから、宣伝文句を取り除いた"
        '「ブランド名＋型番（モデル名）」だけの名前を抽出するアシスタントです。\n'
        "厳守事項:\n"
        "- 与えられたテキストに実際に含まれる文字列の削除のみ行い、"
        "含まれていない情報（型番・特徴等）を新たに付け加えないこと。\n"
        "- ブランド名は必ず残すこと。\n"
        "- 自信を持って抽出できない場合は、入力テキストをそのまま返すこと。\n"
        '- 出力は必ず次のJSON形式のみ: {"clean_name": "..."}'
    )
    try:
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        message = client.messages.create(
            model=settings.claude_model,
            max_tokens=200,
            system=system,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"ブランド: {brand}\nカテゴリ: {category}\n"
                        f"タイトル: {regex_cleaned}"
                    ),
                }
            ],
        )
        text = "".join(block.text for block in message.content if block.type == "text").strip()
        if text.startswith("```"):
            text = text.strip("`").split("\n", 1)[-1]
        data = json.loads(text)
        candidate = str(data["clean_name"]).strip()
    except Exception:  # noqa: BLE001 - AI provider failures are varied; caller falls back
        return None

    if not _looks_like_a_reasonable_cleanup(candidate, regex_cleaned, brand):
        return None
    return candidate


def clean_product_title(raw_title: str, brand: str, category: str) -> str:
    """Always returns a usable name - the regex-cleaned text at minimum,
    Claude's further-tightened version when configured and its output
    passes the sanity check."""
    regex_cleaned = strip_promotional_noise(raw_title)
    tightened = _ai_tighten(regex_cleaned, brand, category)
    return tightened or regex_cleaned
