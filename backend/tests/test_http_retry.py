import httpx
import pytest

from app import http_retry


def test_returns_response_on_first_success(monkeypatch):
    calls = []

    def fake_get(url, params=None, headers=None, timeout=None):
        calls.append(1)
        return httpx.Response(200, json={"ok": True}, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)
    response = http_retry.get_with_retry("https://example.com", params={}, timeout=5.0)
    assert response.status_code == 200
    assert len(calls) == 1


def test_retries_on_retryable_status_then_succeeds(monkeypatch):
    calls = []

    def fake_get(url, params=None, headers=None, timeout=None):
        calls.append(1)
        if len(calls) < 3:
            return httpx.Response(503, text="busy", request=httpx.Request("GET", url))
        return httpx.Response(200, json={"ok": True}, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)
    monkeypatch.setattr(http_retry.time, "sleep", lambda _seconds: None)

    response = http_retry.get_with_retry("https://example.com", params={}, timeout=5.0, max_retries=2)
    assert response.status_code == 200
    assert len(calls) == 3


def test_returns_final_error_response_after_exhausting_retries(monkeypatch):
    calls = []

    def fake_get(url, params=None, headers=None, timeout=None):
        calls.append(1)
        return httpx.Response(500, text="down", request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)
    monkeypatch.setattr(http_retry.time, "sleep", lambda _seconds: None)

    response = http_retry.get_with_retry("https://example.com", params={}, timeout=5.0, max_retries=2)
    assert response.status_code == 500
    assert len(calls) == 3  # 1 initial + 2 retries


def test_does_not_retry_non_retryable_status(monkeypatch):
    calls = []

    def fake_get(url, params=None, headers=None, timeout=None):
        calls.append(1)
        return httpx.Response(400, text="bad request", request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)
    response = http_retry.get_with_retry("https://example.com", params={}, timeout=5.0, max_retries=2)
    assert response.status_code == 400
    assert len(calls) == 1


def test_raises_last_exception_when_every_attempt_fails_to_connect(monkeypatch):
    def fake_get(url, params=None, headers=None, timeout=None):
        raise httpx.ConnectTimeout("timed out", request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)
    monkeypatch.setattr(http_retry.time, "sleep", lambda _seconds: None)

    with pytest.raises(httpx.ConnectTimeout):
        http_retry.get_with_retry("https://example.com", params={}, timeout=5.0, max_retries=2)


def test_custom_is_retryable_can_stop_retrying_a_normally_retryable_status(monkeypatch):
    """A custom `is_retryable` lets a caller treat a status normally in
    RETRYABLE_STATUS_CODES (like 429) as permanent based on the response
    body - e.g. Yahoo's quota-exhaustion 429, which retrying can't fix."""
    calls = []

    def fake_get(url, params=None, headers=None, timeout=None):
        calls.append(1)
        return httpx.Response(429, text="quota exhausted forever", request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)
    monkeypatch.setattr(http_retry.time, "sleep", lambda _seconds: None)

    response = http_retry.get_with_retry(
        "https://example.com",
        params={},
        timeout=5.0,
        max_retries=2,
        is_retryable=lambda r: "quota exhausted" not in r.text,
    )
    assert response.status_code == 429
    assert len(calls) == 1


def test_recovers_after_a_transient_connect_timeout(monkeypatch):
    calls = []

    def fake_get(url, params=None, headers=None, timeout=None):
        calls.append(1)
        if len(calls) == 1:
            raise httpx.ConnectTimeout("timed out", request=httpx.Request("GET", url))
        return httpx.Response(200, json={"ok": True}, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx, "get", fake_get)
    monkeypatch.setattr(http_retry.time, "sleep", lambda _seconds: None)

    response = http_retry.get_with_retry("https://example.com", params={}, timeout=5.0, max_retries=2)
    assert response.status_code == 200
    assert len(calls) == 2
