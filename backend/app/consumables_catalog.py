"""Seed list for the STEP52 consumables corner (app/consumables_merchandiser.py).

Real, widely-sold consumables. Loaded idempotently by scripts/init_db.py
(new slugs are inserted; an existing row is never overwritten, so prices,
history and any msrp an admin has set survive every deploy).

msrp is deliberately None for every item: a list price is only entered
once it has been verified against the maker's own published price - an
estimated one would make a "〇% OFF" a false 二重価格表示. Until then the
corner compares against PAR.'s own recorded prices (the 30-day median),
which needs no outside claim at all.

match_tokens: "," separates groups that must ALL appear in a Rakuten
listing's name; "|" separates alternative spellings within a group
(listings mix katakana and Latin brand names). Compared case- and
space-insensitively.

seasons: which seasons (merchandiser.SEASONS keys) this item is
especially relevant to - drives the seasonal ordering and copy.
"""

CONSUMABLES = [
    {
        "slug": "footjoy-weathersof-glove",
        "kind": "glove",
        "brand": "FootJoy",
        "name": "ウェザーソフ グローブ",
        "search_keyword": "フットジョイ ウェザーソフ グローブ",
        "match_tokens": "フットジョイ|footjoy,ウェザーソフ|weathersof",
        "seasons": "spring,summer,autumn,rainy",
    },
    {
        "slug": "footjoy-raingrip-glove",
        "kind": "glove",
        "brand": "FootJoy",
        "name": "レイングリップ グローブ（雨用・両手）",
        "search_keyword": "フットジョイ レイングリップ グローブ",
        "match_tokens": "フットジョイ|footjoy,レイングリップ|raingrip",
        "seasons": "rainy,summer",
    },
    {
        "slug": "footjoy-wintersof-glove",
        "kind": "glove",
        "brand": "FootJoy",
        "name": "ウィンターソフ グローブ（冬用・両手）",
        "search_keyword": "フットジョイ ウィンターソフ グローブ",
        "match_tokens": "フットジョイ|footjoy,ウィンターソフ|wintersof",
        "seasons": "winter",
    },
    {
        "slug": "lite-wood-long-tee",
        "kind": "tee",
        "brand": "LITE",
        "name": "ウッドティー ロング",
        "search_keyword": "ライト ウッドティー ロング",
        "match_tokens": "ライト|lite,ウッドティー|ウッド ティー,ロング",
        "seasons": "spring,autumn",
    },
    {
        "slug": "tabata-golf-tee",
        "kind": "tee",
        "brand": "Tabata",
        "name": "ゴルフティー",
        "search_keyword": "タバタ ゴルフティー",
        "match_tokens": "タバタ|tabata,ティー",
        "seasons": "spring,autumn",
    },
    {
        "slug": "lite-grip-cleaner",
        "kind": "care",
        "brand": "LITE",
        "name": "グリップクリーナー",
        "search_keyword": "ライト グリップクリーナー ゴルフ",
        "match_tokens": "ライト|lite,グリップクリーナー|グリップ クリーナー",
        "seasons": "rainy,summer",
    },
    {
        "slug": "dunlop-ddh-ball",
        "kind": "ball",
        "brand": "DUNLOP",
        "name": "DDH ゴルフボール",
        "search_keyword": "ダンロップ DDH ゴルフボール",
        "match_tokens": "ddh,ダンロップ|dunlop|ボール",
        "seasons": "spring,autumn",
    },
]
