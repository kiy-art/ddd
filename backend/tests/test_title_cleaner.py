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
