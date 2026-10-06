"""STEP74: Rakuten search keywords built from product names."""

import pytest

from app import discovery
from app.search_keyword import MAX_KEYWORD_CHARS, build_search_keyword, is_valid_rakuten_keyword

# Real product names whose "brand + name" keyword Rakuten rejected with HTTP 400
# on 2026-10-04 (production error log).
FAILED_IN_PRODUCTION = [
    ("PING", "ピン G440K ドライバー ALTA J CB BLUE G440 K 右用"),
    ("TaylorMade", "テーラーメイド Qi ウィ アイアン / ELDIO TM40"),
    ("Srixon", "ダンロップ スリクソン 2025 Zスター XV ［ まとめ買い ］ ダンロップ Z-STAR XV まとめ買い"),
    ("PING", "ー PING G440 MAX ドライバー TOUR 2.0 CHROME 65 G440 MAX ドライバー ツアー2.0 クロム65"),
    ("Bridgestone", "ブリヂストン 2022 ツアー ビー シリーズ TOUR B"),
    ("Bridgestone", "ブリヂストンゴルフ NEW TOUR B X／TOUR B XS ( 入) 2026"),
    ("Titleist", "Titleist 「 PRO V1 」、「 PRO V1x 」 2025モデル (12個入)"),
    ("Srixon", "スリクソン ZXi7 アイアン6本セット ≪ ≫ - DUNLOP アイアンセット ダンロップ 5番/6番/7番/8番/9番/PW ZM-C704"),
    (
        "PING",
        "ピン G440 アイアン G440 IRON NEO ネオ スチール 1本 3本 4本 5本 6本 セット g440 iron ジー440 950NEO "
        "950ネオ G440アイアン G440IRON 日本仕様 右用 左用 レフト ー アイアンセット 単品アイアン",
    ),
]


@pytest.mark.parametrize("brand,name", FAILED_IN_PRODUCTION)
def test_rejected_names_become_valid_keywords(brand, name):
    assert not is_valid_rakuten_keyword(f"{brand} {name}")
    keyword = build_search_keyword(brand, name)
    assert keyword is not None and is_valid_rakuten_keyword(keyword)
    assert len(keyword) < MAX_KEYWORD_CHARS


def test_model_numbers_survive_the_rebuild():
    keyword = build_search_keyword("PING", "ピン G440K ドライバー ALTA J CB BLUE G440 K 右用")
    assert "G440K" in keyword and "ALTA" in keyword
    # STEP75: a lone "J"/"K" is dropped - Rakuten rejects it even in full width.
    assert not any(t in keyword.split() for t in ("J", "K", "Ｊ", "Ｋ"))
    assert "TM40" in build_search_keyword("TaylorMade", "テーラーメイド Qi ウィ アイアン / ELDIO TM40")


def test_lone_non_kanji_characters_are_dropped():
    """STEP75: every one of the 81 widened keywords (e.g. "TYPE Ｓ") was
    rejected on 2026-10-06, and so were lone kana ("ス", "の")."""
    assert build_search_keyword("Yonex", "EZONE GT TYPE S ドライバー") == "Yonex EZONE GT TYPE ドライバー"
    assert not is_valid_rakuten_keyword("PING TYPE Ｓ")
    assert not is_valid_rakuten_keyword("PING ス コントロール")
    assert not is_valid_rakuten_keyword("PING 9本 の セット")
    assert build_search_keyword("PING", "パター ス コントロール") == "PING パター コントロール"


def test_too_broad_after_dropping_is_no_keyword():
    """Audit 2026-10-06: the brand in another spelling, or the brand plus
    one word, would match far too many listings."""
    assert build_search_keyword("PING", "B") is None
    assert build_search_keyword("Bridgestone", "BRIDGESTONE B") is None
    assert build_search_keyword("Bridgestone", "ブリヂストン X") is None
    assert build_search_keyword("PING", "ピン K") is None
    assert build_search_keyword("Bridgestone", "TOUR B X") is None


@pytest.mark.parametrize(
    "brand,name",
    [
        ("PING", "G440 MAX ドライバー"),
        ("Titleist", "PRO V1x 2025"),
        ("L.A.B. Golf", "MEZZ.1 FR-5 パター"),
        ("Honma", "T//WORLD for the Queen 白"),
    ],
)
def test_valid_keywords_are_left_exactly_as_they_were(brand, name):
    # Products that fetch fine today must keep matching the same listings.
    assert build_search_keyword(brand, name) == f"{brand} {name}"


def test_symbol_only_tokens_and_length_are_rejected():
    assert not is_valid_rakuten_keyword("PING ー G440")
    assert not is_valid_rakuten_keyword("PING ／ G440")
    assert not is_valid_rakuten_keyword("PING " + "あ" * 130)
    assert is_valid_rakuten_keyword("PING 白 G440")  # one kanji is accepted (seen passing in production)


def test_long_names_are_cut_at_a_token_boundary():
    name = " ".join(f"モデル{i}" for i in range(60))
    keyword = build_search_keyword("PING", name)
    assert keyword is not None and len(keyword) <= 100
    assert keyword.split(" ")[-1].startswith("モデル")


def test_nothing_usable_returns_none():
    assert build_search_keyword("", "") is None
    assert build_search_keyword("", "／ ー ・") is None


def test_brand_is_added_when_the_name_lost_it():
    assert build_search_keyword("Titleist", "「 PRO V1 」 / 2025").startswith("Titleist ")


def test_no_discovery_keyword_is_invalid():
    for keywords in discovery.CATEGORY_SEARCH_KEYWORDS.values():
        for keyword in keywords:
            assert is_valid_rakuten_keyword(keyword), keyword
