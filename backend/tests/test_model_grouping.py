"""Same-model grouping is dry-run only and must never join different specs."""

from types import SimpleNamespace

import pytest

from app import model_grouping as mg


def _p(id, name, brand="TaylorMade", category="putter", price=66000, pending=False, slug=None):
    return SimpleNamespace(
        id=id, name=name, brand=brand, category=category, current_price=price,
        pending_review=pending, slug=slug or f"s{id}", price_history=[],
    )


def _groups(*products):
    return mg.plan_model_grouping(list(products)).groups


def test_spider_zt_standard_wordings_group_together():
    groups = _groups(
        _p(1, "テーラーメイド スパイダーZT パター スタンダード"),
        _p(2, "Taylormade Spider ZT STANDARD スパイダーZT パター"),
        _p(3, "テーラーメイド Spider ZT STANDARD / STEEL SHAFT"),
    )
    assert len(groups) == 1 and len(groups[0].members) == 3 and groups[0].status == "auto"


@pytest.mark.parametrize(
    "other",
    [
        "テーラーメイド Spider ZT MAX LONG スパイダー ゼロトルク マックス ロング パター",  # other head/length
        "テーラーメイド Spider ZT BLACK Single Line パター",
        "テーラーメイド スパイダーZT Spider 5K-ZT STANDARD パター",  # different model (5K)
        "テーラーメイド スパイダー ZT STANDARD パター(ロフト3.5度)",  # loft stated
        "テーラーメイド スパイダー ZT STANDARD パター 34インチ",  # length stated
        "テーラーメイド スパイダー ZT STANDARD パター LH レフト",  # left-handed
    ],
)
def test_different_spec_is_not_grouped_with_standard(other):
    assert _groups(_p(1, "Taylormade Spider ZT STANDARD スパイダーZT パター"), _p(2, other)) == []


def test_putter_without_variant_is_not_keyed():
    key, reason = mg.extract_key("TaylorMade", "putter", "TaylorMade Spider ZT Putter スパイダー ZT パター")
    assert key is None and "型" in reason


def test_iron_groups_ignore_shaft_but_not_set_size():
    base = "ダンロップ SRIXON ZXi5 アイアン 6本セット"
    groups = _groups(
        _p(1, base + " TOUR 105", "Srixon", "iron", 171600),
        _p(2, base + " neo", "Srixon", "iron", 171600),
        _p(3, "ダンロップ SRIXON ZXi5 アイアン 5本セット(#6-PW) neo", "Srixon", "iron", 140000),
    )
    assert len(groups) == 1 and {p.id for p in groups[0].members} == {1, 2}


def test_single_club_and_selectable_iron_never_keyed():
    for name in ("SRIXON ZXi5 アイアン 単品", "SRIXON ZXi5 アイアン 1本 3本 4本 5本 6本 セット", "SRIXON ZXi5 アイアン"):
        key, _ = mg.extract_key("Srixon", "iron", name)
        assert key is None


def test_zx4_generations_and_years_are_separate_keys():
    a, _ = mg.extract_key("Srixon", "iron", "スリクソン ZX4 アイアン 6本セット")
    b, _ = mg.extract_key("Srixon", "iron", "スリクソン ZX4 Mk II アイアン 6本セット")
    c, _ = mg.extract_key("Srixon", "iron", "スリクソン 2023 ZX4 Mk II アイアン 6本セット")
    assert len({a, b, c}) == 3


def test_zxi_is_not_zx_line():
    key, _ = mg.extract_key("Srixon", "iron", "SRIXON ZXi5 アイアン 6本セット")
    assert key.line == "ZXi5"
    key, _ = mg.extract_key("Srixon", "iron", "SRIXON ZX5 Mk II アイアン 6本セット")
    assert key.line == "ZX5 Mk II"


def test_other_brand_or_unlisted_line_is_never_keyed():
    key, reason = mg.extract_key("PING", "iron", "PING G430 アイアン 6本セット")
    assert key is None and "表外" in reason


def test_price_spread_sends_group_to_review():
    groups = _groups(
        _p(1, "Taylormade Spider ZT STANDARD パター", price=66000),
        _p(2, "テーラーメイド スパイダーZT パター スタンダード", price=99800),
    )
    assert groups[0].status == "review" and "価格差" in groups[0].reasons[0]


def test_survivor_prefers_published_then_search_impressions():
    p1 = _p(1, "Taylormade Spider ZT STANDARD パター", pending=True)
    p2 = _p(2, "テーラーメイド スパイダーZT パター スタンダード")
    p3 = _p(3, "テーラーメイド Spider ZT STANDARD パター", slug="best")
    plan = mg.plan_model_grouping([p1, p2, p3], impressions={"best": 40})
    assert plan.groups[0].survivor.id == 3


def test_plan_is_read_only_and_says_dry_run():
    plan = mg.plan_model_grouping([_p(1, "Taylormade Spider ZT STANDARD パター")])
    assert plan.groups == [] and "dry-run" in plan.plan_lines[-1]
