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


def test_msrp_estimate_basis_skips_the_live_api_call_even_when_configured(monkeypatch):
    """STEP21: a buy_score derived from analysis.AnalysisResult.data_basis
    == "msrp_estimate" (see app/analysis.py) isn't backed by real trend
    data, so generate_ai_content must fall back to rule-based wording
    without ever calling the real Claude API - even with an API key
    configured - so this STEP doesn't silently start spending more on AI
    calls. Proven here by making a real call raise, not just by asserting
    on the output."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    from app.config import get_settings

    get_settings.cache_clear()
    try:
        import anthropic

        class _ClientThatMustNotBeCalled:
            def __init__(self, **kwargs):
                raise AssertionError("anthropic.Anthropic() must not be constructed for an msrp_estimate verdict")

        monkeypatch.setattr(anthropic, "Anthropic", _ClientThatMustNotBeCalled)

        result = analysis.analyze_prices(7500, [(10000, _days_ago(5))], msrp=10000)
        assert result.data_basis == "msrp_estimate"

        content, error = ai.generate_ai_content_safe("New Ball", "Titleist", result)

        assert error is None
        assert content.source == "rule_based"
        assert "暫定" in content.summary
    finally:
        get_settings.cache_clear()
