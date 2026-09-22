"""Canonical golf-brand name recognition, shared by app/discovery.py
(matching a Rakuten/Yahoo listing's raw title to one of this catalog's
known brands), app/popularity.py (matching a ranking entry's title the
same way), and app/title_cleaner.py (deduping redundant repeats of a
brand's own other spellings - see BRAND_NAME_SYNONYMS below). Lives in
its own module specifically so none of those need to import each other
just for this.
"""

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
}


def match_brand(item_name: str) -> str | None:
    lowered = item_name.lower()
    for keyword, brand in BRAND_KEYWORDS.items():
        if keyword.lower() in lowered:
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
    "Honma": ["ホンマ"],
    "Odyssey": ["オデッセイ"],
    "Cleveland": ["クリーブランド"],
    "Yonex": ["ヨネックス"],
    "Fourteen": ["フォーティーン"],
    "Miura": ["三浦技研"],
    "Bettinardi": ["ベティナルディ"],
    "Wilson": ["ウイルソン"],
    "Epon": ["エポン"],
}
