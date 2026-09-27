"""Canonical golf-brand name recognition, shared by app/discovery.py
(matching a Rakuten/Yahoo listing's raw title to one of this catalog's
known brands), app/popularity.py (matching a ranking entry's title the
same way), and app/title_cleaner.py (deduping redundant repeats of a
brand's own other spellings - see BRAND_NAME_SYNONYMS below). Lives in
its own module specifically so none of those need to import each other
just for this.
"""

import re

# Maps a keyword that might appear in a Rakuten item name (English brand
# name or a common Japanese rendering) to this site's canonical brand name
# (matching the brand strings already used across data/*.csv). A listing
# whose name matches none of these is skipped — better to miss a real
# product than to publish one under a guessed/wrong brand.
BRAND_KEYWORDS = {
    "PING": "PING",
    "ピン": "PING",
    "Titleist": "Titleist",
    "タイトリスト": "Titleist",
    "Callaway": "Callaway",
    "キャロウェイ": "Callaway",
    "TaylorMade": "TaylorMade",
    "テーラーメイド": "TaylorMade",
    "Srixon": "Srixon",
    "スリクソン": "Srixon",
    "Bridgestone": "Bridgestone",
    "ブリヂストン": "Bridgestone",
    "ブリジストン": "Bridgestone",
    "Cobra": "Cobra",
    "コブラ": "Cobra",
    "Mizuno": "Mizuno",
    "ミズノ": "Mizuno",
    "XXIO": "XXIO",
    "ゼクシオ": "XXIO",
    "Honma": "Honma",
    "ホンマ": "Honma",
    "本間ゴルフ": "Honma",
    # Vokey is Titleist's wedge line, not a separate manufacturer - matches
    # the brand recorded for it elsewhere in the catalog (see
    # data/real_products_batch3.csv), so a discovered Vokey wedge groups
    # onto the same brand page as other Titleist products instead of
    # fragmenting into its own.
    "Vokey": "Titleist",
    "ボーケイ": "Titleist",
    "Scotty Cameron": "Scotty Cameron",
    "スコッティキャメロン": "Scotty Cameron",
    "スコッティ・キャメロン": "Scotty Cameron",
    "Odyssey": "Odyssey",
    "オデッセイ": "Odyssey",
    "Cleveland": "Cleveland",
    "クリーブランド": "Cleveland",
    "PXG": "PXG",
    "L.A.B Golf": "L.A.B Golf",
    "L.A.B. Golf": "L.A.B Golf",
    "ラブゴルフ": "L.A.B Golf",
    "Yonex": "Yonex",
    "ヨネックス": "Yonex",
    "Fourteen": "Fourteen",
    "フォーティーン": "Fourteen",
    "Miura": "Miura",
    "三浦技研": "Miura",
    "Bettinardi": "Bettinardi",
    "ベティナルディ": "Bettinardi",
    "Wilson": "Wilson",
    "ウイルソン": "Wilson",
    "Epon": "Epon",
    "エポン": "Epon",
    # STEP55: glove / rangefinder makers - without these, every glove and
    # distance-measuring device listing was skipped as "unknown brand".
    "FootJoy": "FootJoy",
    "フットジョイ": "FootJoy",
    "Bushnell": "Bushnell",
    "ブッシュネル": "Bushnell",
    "Nikon": "Nikon",
    "ニコン": "Nikon",
    "Voice Caddie": "Voice Caddie",
    "ボイスキャディ": "Voice Caddie",
    "Shot Navi": "Shot Navi",
    "ショットナビ": "Shot Navi",
    "Garmin": "Garmin",
    "ガーミン": "Garmin",
    "Yupiteru": "Yupiteru",
    "ユピテル": "Yupiteru",
    # STEP58: makers of small golf accessories (pins, markers, practice
    # gear) for the "その他" category.
    "LITE": "LITE",
    "ライト": "LITE",
    "Tabata": "Tabata",
    "タバタ": "Tabata",
    "DAIYA": "DAIYA",
    "ダイヤゴルフ": "DAIYA",
    "ダイヤ": "DAIYA",
}

# "ピン" (PING's katakana name) is also the start of ordinary words in
# golf listings - "ピンク" (a glove color), "ピンシーカー" (Bushnell's
# rangefinder line), "ピンフラッグ", "ピン型" (a putter head shape) - so it
# only counts as the brand when not followed by more katakana or "型".
#
# Same problem for the accessory makers added in STEP58: "ライト" is also
# "ライトグリーン" / "ハイライト" / "ライトウェイト", and "ダイヤ" is also
# "ダイヤモンド" - so they only count as a whole katakana word.
KEYWORD_PATTERNS = {
    "ピン": re.compile(r"ピン(?![ァ-ヶー型])"),
    "ライト": re.compile(r"(?<![ァ-ヶー])ライト(?![ァ-ヶー])"),
    "ダイヤ": re.compile(r"(?<![ァ-ヶー])ダイヤ(?![ァ-ヶー])"),
    "LITE": re.compile(r"\bLITE\b"),
}


def keyword_in(keyword: str, item_name: str) -> bool:
    pattern = KEYWORD_PATTERNS.get(keyword)
    if pattern is not None:
        return bool(pattern.search(item_name))
    return keyword.lower() in item_name.lower()


def match_brand(item_name: str) -> str | None:
    for keyword, brand in BRAND_KEYWORDS.items():
        if keyword_in(keyword, item_name):
            return brand
    return None


# True "same name, different script" pairs only - NOT the category/
# sub-brand groupings BRAND_KEYWORDS above also encodes (e.g. "Vokey"/
# "ボーケイ" -> "Titleist" is a real, distinct product line that happens to
# be sold under the Titleist umbrella; treating it as a synonym of
# "Titleist" itself would delete real, distinguishing model info from a
# cleaned title, not a duplicate). Used by title_cleaner.py to collapse a
# shop repeating a brand's own name in two scripts down to one mention.
BRAND_NAME_SYNONYMS: dict[str, list[str]] = {
    "PING": ["ピン"],
    "Titleist": ["タイトリスト"],
    "Callaway": ["キャロウェイ"],
    "TaylorMade": ["テーラーメイド"],
    "Srixon": ["スリクソン"],
    "Bridgestone": ["ブリヂストン", "ブリジストン"],
    "Cobra": ["コブラ"],
    "Mizuno": ["ミズノ"],
    "XXIO": ["ゼクシオ"],
    # Kanji "本間ゴルフ" is the maker's own registered name -
    # without it a title like "本間ゴルフ TW757 ..." never counted as naming
    # the brand, so title_cleaner's AI result was rejected as "brand
    # missing" and the raw listing title was kept. Longest-first matching
    # in title_cleaner means "ホンマゴルフ" is consumed whole, not as
    # "ホンマ" + a stray "ゴルフ".
    "Honma": ["HONMA GOLF", "本間ゴルフ", "ホンマゴルフ", "ホンマ", "本間"],
    "Odyssey": ["オデッセイ"],
    "Cleveland": ["クリーブランド"],
    "Yonex": ["ヨネックス"],
    # "フォーティン" (no long-vowel mark) is the same shop's own alternate
    # spelling of "フォーティーン", not a different brand (STEP19).
    "Fourteen": ["フォーティーン", "フォーティン"],
    "Miura": ["三浦技研"],
    "Bettinardi": ["ベティナルディ"],
    "Wilson": ["ウイルソン"],
    "Epon": ["エポン"],
    "FootJoy": ["フットジョイ"],
    "Bushnell": ["ブッシュネル"],
    "Nikon": ["ニコン"],
    "Voice Caddie": ["ボイスキャディ"],
    "Shot Navi": ["ショットナビ"],
    "Garmin": ["ガーミン"],
    "Yupiteru": ["ユピテル"],
    "LITE": ["ライト"],
    "Tabata": ["タバタ"],
    "DAIYA": ["ダイヤゴルフ", "ダイヤ"],
}
