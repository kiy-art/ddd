from app import title_cleaner


def test_strip_promotional_noise_removes_bracket_tags():
    assert title_cleaner.strip_promotional_noise("【送料無料】PING G440 ドライバー【あす楽】") == "PING G440 ドライバー"


def test_strip_promotional_noise_removes_known_promo_phrases():
    result = title_cleaner.strip_promotional_noise("タイトリスト Titleist Pro V1 ゴルフボール ポイント10倍!!")
    assert "ポイント" not in result
    assert "タイトリスト Titleist Pro V1 ゴルフボール" in result


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
