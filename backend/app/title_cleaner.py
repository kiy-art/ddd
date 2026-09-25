"""Turns a noisy Rakuten/Yahoo listing title into a clean "ブランド＋型番"
product name, so the catalog reads like a price-comparison site instead of
a scrape of shop-specific ad copy (e.g. "【送料無料】タイトリスト Titleist
Pro V1 ゴルフボール ポイント10倍!!" -> "Titleist Pro V1 ゴルフボール").

Two layers, same "rule-based baseline + optional AI enhancement" shape as
app/ai.py and app/x_post.py:

- strip_promotional_noise() is a deterministic regex pass - always runs,
  free, instant - that removes bracket-tag noise (【...】/（...）/[...],
  plus now-empty bracket residue like "［ ］" left over once their contents
  are stripped), date/period-limited sale phrases (including "◯◯年モデル"
  marketing-year labels), coupon copy, quantity/packaging/color notes,
  finish-name and named-shaft-model spec text, handedness/gender
  attributes, municipality names (furusato-nozei reward listings), a
  curated list of common Japanese EC promotional phrases, and redundant
  repeats of the brand's own name in another script. This alone is
  usually enough, and is always the safety-net result.
- clean_product_title() additionally asks Claude to tighten the
  regex-cleaned text down to just "ブランド＋型番" when ANTHROPIC_API_KEY
  is configured. Claude is only ever shown the already-regex-cleaned text
  plus the already-known brand/category (both real, already-matched
  facts - see app/brands.py's match_brand) and is instructed to only
  remove or reformat text that's actually present - e.g. it may fold an
  existing bare year like "2025" into "Pro V1 (2025)", but may never
  invent a fact that isn't already in the text. Its output is
  sanity-checked (non-empty, not much longer than the input, still names
  the known brand in some known spelling) before being trusted; any
  failure - not configured, API error, output that doesn't pass the
  sanity check - falls back to the regex result.

Known limitation (regex layer only): a shop repeating the MODEL number
itself in another script or spelling - e.g. "OPUS SP" ... "オーパス
エスピー", "PRO V1" ... "プロV1", "FR-3" ... "FR3", or a brand name's own
long-vowel-mark variant slipping through without being in
app/brands.py's BRAND_NAME_SYNONYMS - isn't something
strip_promotional_noise() can recognize (unlike a fixed brand-name
dictionary, there's no bounded list of every model's alternate spelling
to check against). Only the Claude-assisted path collapses that; see
tests/test_title_cleaner.py's AI-configured tests for confirmation this
works when ANTHROPIC_API_KEY is set (as it is in production - see
docs/ai_company_guidelines.md).
"""

import json
import re

from app.brands import BRAND_NAME_SYNONYMS
from app.config import get_settings

# Bracket-tag segments (【...】, （...）, full/half-width [...]) are
# virtually always shop promotional tags in this domain ("【送料無料】",
# "【あす楽】", "（12球入り×3箱）") - a real model name is essentially never
# wrapped in these, so they're stripped wholesale regardless of content.
# Half-width "(...)" is deliberately NOT included here - shops use it for
# the same noise, but also occasionally for a real spec note, so that one
# is left to the more targeted patterns below instead of a blanket strip.
_BRACKET_TAG_PATTERN = re.compile(r"[【\[（][^】\]）]*[】\]）]")

# "9/23まで" / "9月23日まで" / "本日限定" - date- or period-limited sale
# copy. A fixed calendar cutoff has no place in a product's own name.
_DATE_LIMIT_PATTERN = re.compile(r"\d{1,2}/\d{1,2}まで|\d{1,2}月\d{1,2}日まで|本日限定|今だけ")

# "2026年モデル" - strips only the "年モデル" marketing-label wording,
# keeping the year digits themselves (STEP23; was a blanket strip of the
# whole match through STEP19-22, which meant "2023年モデル" and "2025年
# モデル" both collapsed to nothing and merged as if they were the same
# product - wrong for something like a golf ball with a real ~2-year
# release cycle, where the year genuinely is a distinguishing generation,
# not filler). Left with a bare year, e.g. "2023", which is exactly the
# form the module docstring's known limitation already covers: kept as-is
# by this regex layer, and optionally folded into "モデル名 (年)" by the
# AI-assisted layer when meaningful.
_YEAR_MODEL_PATTERN = re.compile(r"(\d{4})年モデル")

# Named shaft models ("N.S.PRO TS-114w Ver2", "NSプロ", "DS-91w") - real
# spec info a shop lists, but a bundled shaft's own model number, not
# part of what the CLUB itself is. Hand-picked shaft-brand prefixes
# (rather than a generic "alphanumeric code" pattern) so this can't
# accidentally eat a club's own model number, like "FR-3" or "G440".
# The model-code group is "at most one" (STEP23; was "zero or more"
# through STEP19-22) - a greedy repeated group here would keep consuming
# any later space-separated alphanumeric run too, e.g. a bare year like
# "2026" sitting right after "Ver2" in the same title, deleting real
# distinguishing info far past the shaft spec itself.
_SHAFT_SPEC_PATTERN = re.compile(
    r"N\.?S\.?\s*PRO(?:\s*[A-Za-z0-9\-]+)?(?:\s*Ver\.?\s*\d+)?"
    r"|NSプロ(?:\s*[A-Za-z0-9\-]+)?(?:\s*Ver\.?\s*\d+)?"
    r"|DS-91w",
    re.IGNORECASE,
)

# Quantity/packaging notes ("3ダースセット", "12球入り", "(12球)", "×3箱")
# - real information about a specific listing's bundle, but not part of
# the product's own name (the same reasoning STEP15 already applied to
# "送料無料" etc.: useful to a shopper, not to what the product IS).
# "入り" is optional (STEP23) - a shop parenthetical like "(12球)" names
# the same ball count without that suffix, and previously survived as
# leftover noise since half-width "(...)" isn't blanket-stripped (see
# _BRACKET_TAG_PATTERN's own comment on why).
_QUANTITY_PATTERN = re.compile(r"\d+ダース(?:セット)?|\d+球(?:入り)?|×?\d+箱")

# Common Japanese EC promotional phrases that appear even on otherwise
# legitimate listings (unlike ACCESSORY_KEYWORDS/AUTO_PUBLISH_NG_KEYWORDS/
# NON_RETAIL_LISTING_KEYWORDS in discovery.py/pipeline.py, which mark a
# listing as not worth registering at all - see those modules' own
# comments for why "送料無料"/"ポイント"/"得" specifically must NOT be
# treated as reject signals: they appear on nearly every real listing,
# including genuine golf clubs, so rejecting candidates on them would
# break normal discovery/price-matching. Here they only ever remove text
# from the display name, never the product itself).
#
# "ゴルフクラブ"/"ゴルフボール" are included deliberately even though they
# describe the real product category: this catalog already records
# category on the Product row itself (never parsed from the display
# name), and STEP18 asked for names trimmed down to brand+model only - a
# bare, generic category noun in the title is exactly the kind of shop
# boilerplate that goal is about, same spirit as stripping "新品"/"正規品".
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
    "ギフト",
    "プレゼント",
    "選べるシャフト",
    "ロフト角",
    "ゴルフクラブ",
    "ゴルフボール",
    # Bare "ボール" - not "ゴルフボール" above, but the same shop habit of
    # tacking the generic category noun onto the end (STEP19).
    "ボール",
    # "パール" + color (STEP23) - a golf-ball colorway prefix ("パール
    # ホワイト" etc.). Listed before the bare color words below so the
    # whole compound is removed in one match; without this, only the
    # "ホワイト" portion matched, leaving a dangling "パール" behind.
    "パールホワイト",
    "パールイエロー",
    # Common shop colorway suffixes - occasionally a genuine distinguishing
    # variant, but usually just shop-added packaging info in this domain;
    # STEP18 asked for these removed (e.g. "...3ダースセット ホワイト").
    "ホワイト",
    "イエロー",
    "ブラック",
    "レッド",
    "ブルー",
    "グリーン",
    "オレンジ",
    "ピンク",
    "シルバー",
    "ゴールド",
    "パープル",
    "ネイビー",
    # Coupon copy (STEP19) - like "送料無料"/"ポイント◯倍" above, this
    # appears on nearly every listing regardless of the product itself.
    r"最大\d+%OFF",
    "クーポン発行中",
    "クーポン",
    # Finish/plating names (STEP19) - real spec info, but describe a
    # specific unit's coating, not what the model IS.
    "パールサテン",
    "ダイヤモンドブラックサテン",
    # Handedness/gender attributes (STEP19) - a purchase option, not part
    # of the product's own name (this catalog doesn't track handedness).
    "右利き用",
    "左利き用",
    "レフティ",
    "メンズ",
    "レディース",
]
_PROMO_PATTERN = re.compile("|".join(_PROMO_PHRASES))

# Japanese municipality names ("千葉県柏市") - the giveaway of a furusato-
# nozei (ふるさと納税) donation-reward listing's title. Discovery already
# rejects candidates whose title contains "ふるさと納税"/"ふるさと" outright
# (see pipeline.NON_RETAIL_LISTING_KEYWORDS) - this is a second, narrower
# net for when a listing's title names the municipality without ever
# spelling out "ふるさと納税" itself. Restricted to kana/kanji so it can't
# match inside a Latin-script model number.
_MUNICIPALITY_PATTERN = re.compile(
    r"[ぁ-んァ-ヶー一-龯]{1,8}(?:都|道|府|県)(?:[ぁ-んァ-ヶー一-龯]{1,10}(?:市|区|町|村))?"
    r"|[ぁ-んァ-ヶー一-龯]{1,10}(?:市|区|町|村)"
)

# Runs of punctuation/symbols shops use for emphasis (!!, ★, ◆, ~, ×) once
# the text they were decorating has already been stripped out around them.
_DECORATION_PATTERN = re.compile(r"[!!★☆◆■□▼▲♪♫~〜×]+")

# A bracket pair left with nothing (or just whitespace) inside - either
# already empty in the raw listing ("［ ］", seemingly a shop template
# placeholder never filled in), or emptied out by _BRACKET_TAG_PATTERN
# above stripping its contents. Every bracket style this domain uses,
# including the two half-width parens/full-width square brackets that
# _BRACKET_TAG_PATTERN above deliberately leaves alone when they hold
# real content (STEP19).
_EMPTY_BRACKET_PATTERN = re.compile(r"[［\[（(]\s*[］\]）)]")

_WHITESPACE_PATTERN = re.compile(r"[\s　]+")


def _dedupe_brand_name_repeats(text: str, brand: str) -> str:
    """Once the brand's name has appeared once (in any of its known
    spellings - see app/brands.py's BRAND_NAME_SYNONYMS), later repeats of
    ANY spelling of that same brand are the shop just repeating itself
    (e.g. "キャロウェイ ... callaway" for the same product) and are
    removed; the first-seen spelling is kept as-is.

    Deliberately its own small, hand-picked synonym list rather than
    discovery.py's BRAND_KEYWORDS: that dict also maps distinct sub-brand/
    product-line names (e.g. "Vokey"/"ボーケイ" -> "Titleist") onto a
    parent brand purely for site navigation - stripping those here would
    delete real, distinguishing model info, not a duplicate.
    """
    synonyms = BRAND_NAME_SYNONYMS.get(brand)
    if not synonyms:
        return text
    all_spellings = sorted({brand, *synonyms}, key=len, reverse=True)
    pattern = re.compile("|".join(re.escape(s) for s in all_spellings), re.IGNORECASE)

    seen = False

    def _replace(match: re.Match) -> str:
        nonlocal seen
        if not seen:
            seen = True
            return match.group(0)
        return " "

    return pattern.sub(_replace, text)


def strip_promotional_noise(raw_title: str, brand: str | None = None) -> str:
    text = _BRACKET_TAG_PATTERN.sub(" ", raw_title)
    text = _DATE_LIMIT_PATTERN.sub(" ", text)
    text = _YEAR_MODEL_PATTERN.sub(r"\1", text)  # keep the year, drop only "年モデル"
    text = _QUANTITY_PATTERN.sub(" ", text)
    text = _PROMO_PATTERN.sub(" ", text)
    text = _SHAFT_SPEC_PATTERN.sub(" ", text)
    text = _MUNICIPALITY_PATTERN.sub(" ", text)
    text = _DECORATION_PATTERN.sub(" ", text)
    if brand:
        text = _dedupe_brand_name_repeats(text, brand)
    # Run after content-stripping (which can itself empty out a bracket
    # pair) and after brand dedup, so anything either pass hollowed out
    # gets swept up too.
    text = _EMPTY_BRACKET_PATTERN.sub(" ", text)
    text = _WHITESPACE_PATTERN.sub(" ", text).strip(" -・/")
    return text or raw_title.strip()


def _looks_like_a_reasonable_cleanup(candidate: str, regex_cleaned: str, brand: str) -> bool:
    if not candidate:
        return False
    if len(candidate) > len(regex_cleaned) + 10:
        return False  # Claude added text rather than only removing it
    # Any known spelling of the brand counts - Claude may (correctly)
    # prefer the katakana form even when the raw title's first mention
    # happened to be the English one, or vice versa.
    acceptable_names = [brand, *BRAND_NAME_SYNONYMS.get(brand, [])]
    return any(name.lower() in candidate.lower() for name in acceptable_names)


def _ai_tighten(regex_cleaned: str, brand: str, category: str) -> str | None:
    settings = get_settings()
    if not settings.anthropic_api_key:
        return None

    import anthropic

    system = (
        "あなたはECサイトの商品タイトルから、宣伝文句を取り除いた"
        '「ブランド名＋型番（モデル名）」だけの名前を抽出するアシスタントです。\n'
        "【出力ルール】商品タイトルは「ブランド名＋主要モデル名」のみとし、"
        "シャフト名、仕上げ名、右利き/左利き等の属性、余計な括弧記号（［ ］等）、"
        "および表記揺れ（長音の有無・全角半角・英語/カタカナ等）による重複は"
        "すべて削ぎ落としなさい。\n"
        "厳守事項:\n"
        "- 与えられたテキストに実際に含まれる文字列の削除・整理のみ行い、"
        "含まれていない新しい情報（型番・特徴等）を付け加えないこと。"
        "ただし、テキスト中に実際に存在する年式・年数（例:「2025」）は、"
        "削除する代わりに「モデル名 (年)」のように括弧書きへ整形してもよい"
        "（新事実の追加ではなく、既存の年数の表記整形として扱う）。\n"
        "- ブランド名や型番が英語・カタカナ・長音の有無等、複数の表記で"
        "重複して登場する場合は、最も自然な1つの表記のみを残し、"
        "残りの重複表記は削除すること"
        "（例:「OPUS SP ... オーパス エスピー」→「OPUS SP」のみ残す。"
        "「FR-3 ... FR3」→「FR-3」のみ残す）。\n"
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
    regex_cleaned = strip_promotional_noise(raw_title, brand=brand)
    tightened = _ai_tighten(regex_cleaned, brand, category)
    return tightened or regex_cleaned
