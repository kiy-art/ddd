import pytest

from app import marketing_playbook as mp


def test_valid_copy_using_only_given_numbers_passes():
    mp.validate_copy(
        ["PING G440 MAX ドライバー 定価より26.8%安い ¥58,000", "30日平均より6.5%安く、5.8万円で購入できます。"],
        allowed_yen={58000, 62000, 79200},
        allowed_percents={-26.8, -6.5},
    )


def test_rounded_percent_of_a_real_value_passes():
    mp.validate_copy(["定価より約27%安い"], allowed_yen=set(), allowed_percents={-26.8})


@pytest.mark.parametrize("phrase", ["今だけ", "業界最安", "No.1", "残りわずか", "口コミで話題", "必ず値上がり"])
def test_banned_claims_are_rejected(phrase):
    with pytest.raises(mp.ContentPolicyViolation):
        mp.validate_copy([f"PING G440 {phrase}の一本"], allowed_yen=set(), allowed_percents=set())


def test_harmless_caution_wording_is_not_over_blocked():
    mp.validate_copy(
        ["価格は変動する可能性があります。購入前に必ず最新価格をご確認ください。"],
        allowed_yen=set(),
        allowed_percents=set(),
    )


def test_invented_percent_is_rejected():
    with pytest.raises(mp.ContentPolicyViolation):
        mp.validate_copy(["定価より40%安い"], allowed_yen=set(), allowed_percents={-26.8})


def test_invented_price_is_rejected():
    with pytest.raises(mp.ContentPolicyViolation):
        mp.validate_copy(["今なら¥49,800"], allowed_yen={58000}, allowed_percents=set())
    with pytest.raises(mp.ContentPolicyViolation):
        mp.validate_copy(["49,800円で購入可能"], allowed_yen={58000}, allowed_percents=set())
    with pytest.raises(mp.ContentPolicyViolation):
        mp.validate_copy(["約4.9万円"], allowed_yen={58000}, allowed_percents=set())


def test_lowest_price_claim_requires_the_fact_flag():
    with pytest.raises(mp.ContentPolicyViolation):
        mp.validate_copy(["記録上の最安値です"], allowed_yen=set(), allowed_percents=set())
    mp.validate_copy(["記録上の最安値です"], allowed_yen=set(), allowed_percents=set(), allow_lowest_price_claim=True)


def test_goal_specific_prompts_lead_with_the_right_playbook_and_always_include_compliance():
    search = mp.product_copy_system_prompt("search_ctr")
    conversion = mp.product_copy_system_prompt("on_page_conversion")
    routine = mp.product_copy_system_prompt(None)
    for prompt in (search, conversion, routine, mp.guide_system_prompt()):
        assert "景品表示法" in prompt
        assert "ステルスマーケティング" in prompt
    assert search.index("SEO") < search.index("CRO")
    assert conversion.index("CRO") < conversion.index("SEO")
