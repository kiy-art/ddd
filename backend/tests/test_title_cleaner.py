import json

from app import title_cleaner


def test_strip_promotional_noise_removes_bracket_tags():
    assert title_cleaner.strip_promotional_noise("【送料無料】PING G440 ドライバー【あす楽】") == "PING G440 ドライバー"


def test_strip_promotional_noise_removes_known_promo_phrases():
    result = title_cleaner.strip_promotional_noise("タイトリスト Titleist Pro V1 ゴルフボール ポイント10倍!!")
    assert "ポイント" not in result
    assert "ゴルフボール" not in result
    assert "タイトリスト Titleist Pro V1" in result


def test_strip_promotional_noise_removes_wakeari():
    result = title_cleaner.strip_promotional_noise("キャロウェイ ローグ ST MAX ドライバー 訳あり")
    assert "訳あり" not in result
    assert "キャロウェイ ローグ ST MAX ドライバー" in result


def test_strip_promotional_noise_leaves_a_clean_title_unchanged():
    assert title_cleaner.strip_promotional_noise("PING G440 ドライバー") == "PING G440 ドライバー"


def test_strip_promotional_noise_never_returns_empty():
    # A title that's entirely bracket tags/promo phrases still returns
    # something usable (falls back to the original) rather than "".
    result = title_cleaner.strip_promotional_noise("【送料無料】【ポイント10倍】")
    assert result != ""


def test_clean_product_title_falls_back_to_regex_when_ai_not_configured(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        result = title_cleaner.clean_product_title("【送料無料】PING G440 ドライバー", "PING", "driver")
        assert result == "PING G440 ドライバー"
    finally:
        get_settings.cache_clear()


def test_ai_tighten_is_skipped_when_not_configured(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        assert title_cleaner._ai_tighten("PING G440 ドライバー", "PING", "driver") is None
    finally:
        get_settings.cache_clear()


def test_looks_like_a_reasonable_cleanup_rejects_output_missing_the_brand():
    assert title_cleaner._looks_like_a_reasonable_cleanup("何か別の商品名", "PING G440 ドライバー", "PING") is False


def test_looks_like_a_reasonable_cleanup_rejects_output_longer_than_input():
    long_output = "PING G440 ドライバー" + "あ" * 50
    assert title_cleaner._looks_like_a_reasonable_cleanup(long_output, "PING G440 ドライバー", "PING") is False


def test_looks_like_a_reasonable_cleanup_rejects_empty_output():
    assert title_cleaner._looks_like_a_reasonable_cleanup("", "PING G440 ドライバー", "PING") is False


def test_looks_like_a_reasonable_cleanup_accepts_a_valid_tightened_name():
    assert title_cleaner._looks_like_a_reasonable_cleanup("PING G440 ドライバー", "PING G440 ドライバー 2023年モデル", "PING") is True


# --- STEP18: real furusato-nozei / date-limited / set-quantity listings ---


def test_strip_promotional_noise_handles_furusato_gift_example():
    """STEP18 example 1: a furusato-nozei-style reward listing, with
    date/gift/customization boilerplate and the brand name repeated in
    three scripts (キャロウェイ/callaway). The MODEL number itself is also
    repeated phonetically ("OPUS SP" / "オーパス エスピー") - unlike a brand
    name, the regex layer has no dictionary of model transliterations to
    dedupe that against, so it survives here; only the AI-tightened path
    (see test_clean_product_title_ai_tightened_examples below) collapses
    it down to the fully clean "キャロウェイ OPUS SP クロムウェッジ"."""
    raw = "ゴルフクラブ キャロウェイ OPUS SP クロムウェッジ 選べるシャフト ロフト角 callaway オーパス エスピー 千葉県柏市 ギフト プレゼント"
    result = title_cleaner.strip_promotional_noise(raw, brand="Callaway")
    assert result == "キャロウェイ OPUS SP クロムウェッジ オーパス エスピー"
    for noise in ["ゴルフクラブ", "選べるシャフト", "ロフト角", "千葉県柏市", "ギフト", "プレゼント"]:
        assert noise not in result
    assert "callaway" not in result.lower()


def test_strip_promotional_noise_handles_date_limited_set_example():
    """STEP18 example 2: a date-limited sale with dozen/box/color set
    notation. "PRO V1" / "プロV1" is again the model number repeated
    phonetically, not the brand - regex-only can't collapse that (see
    test_clean_product_title_ai_tightened_examples for the AI-tightened
    "タイトリスト Pro V1")."""
    raw = "9/23まで タイトリスト PRO V1 プロV1 ゴルフボール 3ダースセット （12球入り×3箱） ホワイト"
    result = title_cleaner.strip_promotional_noise(raw, brand="Titleist")
    assert result == "タイトリスト PRO V1 プロV1"
    for noise in ["9/23まで", "3ダースセット", "12球入り", "ホワイト", "ゴルフボール"]:
        assert noise not in result


def test_clean_product_title_ai_tightened_examples(monkeypatch):
    """With ANTHROPIC_API_KEY configured, clean_product_title() asks
    Claude to collapse the regex layer's known limitation above (repeated
    model-number transliterations) - verified here against a fake
    anthropic.Anthropic client (no live API call), following the same
    "mock the client, not our own code" shape as the rest of this file's
    ANTHROPIC_API_KEY="" tests exercise the non-AI path."""
    import anthropic

    class _FakeTextBlock:
        type = "text"

        def __init__(self, text):
            self.text = text

    class _FakeMessage:
        def __init__(self, text):
            self.content = [_FakeTextBlock(text)]

    class _FakeMessages:
        def __init__(self, clean_name):
            self._clean_name = clean_name

        def create(self, **kwargs):
            return _FakeMessage(json.dumps({"clean_name": self._clean_name}))

    class _FakeClient:
        def __init__(self, clean_name, **kwargs):
            self.messages = _FakeMessages(clean_name)

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        monkeypatch.setattr(
            anthropic, "Anthropic", lambda api_key: _FakeClient("キャロウェイ OPUS SP クロムウェッジ")
        )
        raw1 = (
            "ゴルフクラブ キャロウェイ OPUS SP クロムウェッジ 選べるシャフト ロフト角 "
            "callaway オーパス エスピー 千葉県柏市 ギフト プレゼント"
        )
        assert title_cleaner.clean_product_title(raw1, "Callaway", "wedge") == "キャロウェイ OPUS SP クロムウェッジ"

        monkeypatch.setattr(anthropic, "Anthropic", lambda api_key: _FakeClient("タイトリスト Pro V1"))
        raw2 = "9/23まで タイトリスト PRO V1 プロV1 ゴルフボール 3ダースセット （12球入り×3箱） ホワイト"
        assert title_cleaner.clean_product_title(raw2, "Titleist", "ball") == "タイトリスト Pro V1"
    finally:
        get_settings.cache_clear()


# --- STEP19: empty-bracket residue / spec phrases / spelling-variant dupes ---


def test_strip_promotional_noise_removes_empty_bracket_residue():
    # A shop template placeholder left blank ("［ ］", full-width brackets)
    # rather than a bracket wrapping real content.
    result = title_cleaner.strip_promotional_noise("タイトリスト Pro V1 ［ ］ ボール")
    assert "［" not in result and "］" not in result
    assert result == "タイトリスト Pro V1"


def test_strip_promotional_noise_removes_year_model_label_wording_but_keeps_the_year():
    # STEP23: "年モデル" is marketing-label wording ("this year's model"),
    # but the year itself often isn't filler - for a product with a real
    # multi-year release cycle (a golf ball, most clubs) it's a genuine
    # distinguishing generation, so only the "年モデル" suffix is removed,
    # not the digits. This also means "2026年モデル" and "2026" (no
    # suffix) now clean down to the identical bare-year form.
    result = title_cleaner.strip_promotional_noise("フォーティーン FR-3 ウェッジ 2026年モデル")
    assert "年モデル" not in result
    assert result == "フォーティーン FR-3 ウェッジ 2026"

    result_with_bare_year = title_cleaner.strip_promotional_noise("タイトリスト Pro V1 2025")
    assert "2025" in result_with_bare_year


def test_strip_promotional_noise_removes_shaft_spec_and_finish_names():
    result = title_cleaner.strip_promotional_noise(
        "フォーティーン FR-3 ウェッジ パールサテン N.S.PRO TS-114w Ver2"
    )
    assert "パールサテン" not in result
    assert "N.S.PRO" not in result
    assert "TS-114w" not in result
    assert "Ver2" not in result
    assert result == "フォーティーン FR-3 ウェッジ"


def test_strip_promotional_noise_removes_handedness_and_coupon_copy():
    result = title_cleaner.strip_promotional_noise(
        "最大10%OFFクーポン発行中 フォーティーン FR-3 ウェッジ 右利き用"
    )
    for noise in ["クーポン", "OFF", "右利き用"]:
        assert noise not in result
    assert result == "フォーティーン FR-3 ウェッジ"


def test_strip_promotional_noise_handles_wedge_spec_and_duplicate_model_example():
    """STEP19 example 1: coupon copy, a named shaft model, a finish name,
    a handedness attribute, and a "◯◯年モデル" marketing-year label all
    stripped. The brand's own long-vowel-mark variant ("フォーティン" - no
    "ー" - vs. "フォーティーン") is now in app/brands.py's
    BRAND_NAME_SYNONYMS, so that repeat collapses too; the trailing bare
    "FR3" (missing the hyphen "FR-3" carries) is a MODEL-number spelling
    variant, not a brand name, so - like STEP18's phonetic model dupes -
    it's left for the AI-tightened path (see
    test_clean_product_title_ai_tightened_step19_examples below). The
    year itself ("2026") now survives as a bare year (STEP23) rather than
    being deleted along with "年モデル" - see
    test_strip_promotional_noise_removes_year_model_label_wording_but_keeps_the_year."""
    raw = (
        "最大10%OFFクーポン発行中 フォーティーン FR-3 ウェッジ パールサテン "
        "N.S.PRO TS-114w Ver2 右利き用 2026年モデル フォーティン FR3 ウェッジ"
    )
    result = title_cleaner.strip_promotional_noise(raw, brand="Fourteen")
    assert result == "フォーティーン FR-3 ウェッジ 2026 FR3 ウェッジ"
    for noise in ["クーポン", "OFF", "パールサテン", "N.S.PRO", "TS-114w", "Ver2", "右利き用", "年モデル", "フォーティン"]:
        assert noise not in result


def test_strip_promotional_noise_handles_empty_bracket_and_duplicate_year_example():
    """STEP19 example 2: coupon copy and an empty full-width-bracket
    placeholder stripped. "プロ V1" (katakana+space) / "PRO V1" (English)
    is again a model-number spelling variant, not a brand repeat - left
    for the AI-tightened path, which also folds the bare "2025" into
    "(2025)" (see test_clean_product_title_ai_tightened_step19_examples)."""
    raw = "最大10%OFFクーポン発行中 タイトリスト 2025 プロ V1 ［ ］ PRO V1 ボール"
    result = title_cleaner.strip_promotional_noise(raw, brand="Titleist")
    assert result == "タイトリスト 2025 プロ V1 PRO V1"
    for noise in ["クーポン", "OFF", "［", "］", "ボール"]:
        assert noise not in result


def test_clean_product_title_ai_tightened_step19_examples(monkeypatch):
    """Final catalog-quality result for both STEP19 examples once Claude
    (mocked - see test_clean_product_title_ai_tightened_examples above for
    why a fake anthropic.Anthropic client rather than a live call) tightens
    the regex-cleaned text per the strengthened system prompt."""
    import anthropic

    class _FakeTextBlock:
        type = "text"

        def __init__(self, text):
            self.text = text

    class _FakeMessage:
        def __init__(self, text):
            self.content = [_FakeTextBlock(text)]

    class _FakeMessages:
        def __init__(self, clean_name):
            self._clean_name = clean_name

        def create(self, **kwargs):
            return _FakeMessage(json.dumps({"clean_name": self._clean_name}))

    class _FakeClient:
        def __init__(self, clean_name, **kwargs):
            self.messages = _FakeMessages(clean_name)

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        monkeypatch.setattr(anthropic, "Anthropic", lambda api_key: _FakeClient("フォーティーン FR-3 ウェッジ"))
        raw1 = (
            "最大10%OFFクーポン発行中 フォーティーン FR-3 ウェッジ パールサテン "
            "N.S.PRO TS-114w Ver2 右利き用 2026年モデル フォーティン FR3 ウェッジ"
        )
        assert title_cleaner.clean_product_title(raw1, "Fourteen", "wedge") == "フォーティーン FR-3 ウェッジ"

        monkeypatch.setattr(anthropic, "Anthropic", lambda api_key: _FakeClient("タイトリスト Pro V1 (2025)"))
        raw2 = "最大10%OFFクーポン発行中 タイトリスト 2025 プロ V1 ［ ］ PRO V1 ボール"
        assert title_cleaner.clean_product_title(raw2, "Titleist", "ball") == "タイトリスト Pro V1 (2025)"
    finally:
        get_settings.cache_clear()


# --- STEP23: Titleist Pro V1 duplicate-card investigation ---


def test_strip_promotional_noise_removes_bare_ball_count_in_half_width_parens():
    # "(12球)" - no "入り" suffix, and half-width parens aren't part of the
    # blanket bracket-tag strip (see _BRACKET_TAG_PATTERN's own comment) -
    # previously survived as leftover noise.
    result = title_cleaner.strip_promotional_noise("タイトリスト Pro V1 ゴルフボール 1ダース(12球)", brand="Titleist")
    assert "12球" not in result
    assert result == "タイトリスト Pro V1"


def test_strip_promotional_noise_removes_pearl_colorway_without_a_dangling_prefix():
    # "パールホワイト" - only the "ホワイト" portion used to match the bare
    # color-word list, leaving a dangling "パール" behind.
    result = title_cleaner.strip_promotional_noise("タイトリスト Pro V1 ゴルフボール パールホワイト", brand="Titleist")
    assert "パール" not in result
    assert result == "タイトリスト Pro V1"


def test_strip_promotional_noise_same_year_pro_v1_listings_converge_to_the_same_name():
    """The actual root cause behind duplicate 'タイトリスト Pro V1' cards
    (STEP23 investigation): two shops list the exact same 2023 ball with
    different set-count/color/spacing boilerplate - after cleaning, both
    must land on the identical string so app/title_migration.py's
    (brand, cleaned_name) grouping merges them into one card."""
    shop_a = "送料無料 タイトリスト Titleist Pro V1 ゴルフボール 1ダース(12球) 2023年モデル"
    shop_b = "あす楽 タイトリスト Pro V1 ゴルフボール 1ダース パールホワイト 2023年モデル"
    result_a = title_cleaner.strip_promotional_noise(shop_a, brand="Titleist")
    result_b = title_cleaner.strip_promotional_noise(shop_b, brand="Titleist")
    assert result_a == result_b == "タイトリスト Pro V1 2023"


def test_strip_promotional_noise_keeps_different_year_pro_v1_listings_apart():
    """A genuine generation difference (2023 vs 2025) must NOT collapse to
    the same name, per the explicit requirement: same-year duplicates
    merge, different-year editions stay separate cards."""
    result_2023 = title_cleaner.strip_promotional_noise(
        "タイトリスト Pro V1 ゴルフボール 1ダース 2023年モデル", brand="Titleist"
    )
    result_2025 = title_cleaner.strip_promotional_noise(
        "タイトリスト Pro V1 ゴルフボール 1ダース 2025年モデル", brand="Titleist"
    )
    assert result_2023 == "タイトリスト Pro V1 2023"
    assert result_2025 == "タイトリスト Pro V1 2025"
    assert result_2023 != result_2025


def test_strip_promotional_noise_keeps_pro_v1_and_pro_v1x_apart():
    # Pro V1 and Pro V1x are different real models (not a set-count/promo
    # variant of each other) - already correctly kept apart before STEP23,
    # verified here as a regression guard since it's easy to accidentally
    # over-generalize a model-number pattern into eating the "x" suffix.
    result_v1 = title_cleaner.strip_promotional_noise("タイトリスト Pro V1 ゴルフボール 1ダース", brand="Titleist")
    result_v1x = title_cleaner.strip_promotional_noise("タイトリスト Pro V1x ゴルフボール 1ダース", brand="Titleist")
    assert result_v1 == "タイトリスト Pro V1"
    assert result_v1x == "タイトリスト Pro V1x"
    assert result_v1 != result_v1x
