import httpx
import pytest

from app import email


def test_raises_when_api_key_missing(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "")
    from app.config import get_settings

    get_settings.cache_clear()
    with pytest.raises(email.ResendNotConfigured):
        email.send_email(to="user@example.com", subject="Test", html="<p>hi</p>")
    get_settings.cache_clear()


def test_send_email_posts_to_resend_with_configured_sender(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "test-key")
    monkeypatch.setenv("RESEND_FROM_EMAIL", "PAR. <onboarding@resend.dev>")
    from app.config import get_settings

    get_settings.cache_clear()

    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return httpx.Response(200, json={"id": "abc123"}, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", fake_post)

    email.send_email(to="user@example.com", subject="値下がり通知", html="<p>hi</p>")

    assert captured["url"] == email.SEND_URL
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["json"]["from"] == "PAR. <onboarding@resend.dev>"
    assert captured["json"]["to"] == ["user@example.com"]
    assert captured["json"]["subject"] == "値下がり通知"

    get_settings.cache_clear()


def test_send_email_raises_on_api_error(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "test-key")
    from app.config import get_settings

    get_settings.cache_clear()

    def fake_post(url, headers=None, json=None, timeout=None):
        return httpx.Response(422, json={"message": "invalid"}, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", fake_post)

    with pytest.raises(email.EmailSendError):
        email.send_email(to="user@example.com", subject="Test", html="<p>hi</p>")

    get_settings.cache_clear()


def test_price_alert_email_html_includes_real_values_only():
    html = email.price_alert_email_html(
        product_name="PING i230 アイアン",
        product_url="https://golf-deals-frontend.onrender.com/products/ping-i230",
        current_price=95000,
        target_price=100000,
    )
    assert "PING i230 アイアン" in html
    assert "95,000" in html
    assert "100,000" in html
    assert "https://golf-deals-frontend.onrender.com/products/ping-i230" in html
