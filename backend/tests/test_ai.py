import datetime

from app import ai, analysis


def _days_ago(n):
    return datetime.datetime.utcnow() - datetime.timedelta(days=n)


def test_fallback_title_is_a_short_headline_not_a_sentence(monkeypatch):
    """Regression test: the fallback title used to be `f"{name} {reason}"`,
    a full sentence, which leaked into page <title>, og:title and
    twitter:title as an ugly wall of text. It must stay a short headline -
    the product name plus a fixed suffix, well under a tweet-length cap."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    from app.config import get_settings

    get_settings.cache_clear()

    history = [(10000, _days_ago(20)), (10000, _days_ago(10))]
    result = analysis.analyze_prices(7900, history)

    content, error = ai.generate_ai_content_safe("PING G440 ドライバー", "PING", result)

    assert error is None
    assert content.title == "PING G440 ドライバーの価格推移・買い時情報"
    assert len(content.title) < 80
    assert "強い買い時" not in content.title  # that belongs in summary, not title
    assert "強い買い時" in content.summary

    get_settings.cache_clear()


def test_fallback_title_for_insufficient_data_is_also_a_short_headline(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    from app.config import get_settings

    get_settings.cache_clear()

    result = analysis.analyze_prices(9500, [])
    content, error = ai.generate_ai_content_safe("New Ball", "Titleist", result)

    assert error is None
    assert content.title == "New Ballの価格推移・買い時情報"

    get_settings.cache_clear()
