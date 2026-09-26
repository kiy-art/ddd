"""Shared retry-with-backoff for the external price-search HTTP calls
(Rakuten/Yahoo). A transient failure (request timeout, connection reset,
or a 429/5xx response) is retried a couple of times with a short backoff
before being handed back to the caller exactly as a single httpx.get()
would have - the caller's own `if response.is_error: raise ...` (or
except clause) still decides whether it's ultimately an error, this just
stops one network blip from becoming a logged failure by itself.

Investigated as part of STEP34's error-log cleanup: fetch_rakuten_prices/
fetch_yahoo_prices (app/pipeline.py) call out to Rakuten/Yahoo once per
product with zero retry, so any transient hiccup during a ~170-product
daily run became a permanent ErrorLog row with no way to distinguish it
from a real, persistent failure."""

import time
from typing import Callable

import httpx

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def get_with_retry(
    url: str,
    *,
    params: dict,
    headers: dict | None = None,
    timeout: float,
    max_retries: int = 2,
    backoff_seconds: float = 0.8,
    is_retryable: Callable[[httpx.Response], bool] | None = None,
) -> httpx.Response:
    """Same contract as httpx.get(url, params=..., headers=..., timeout=...)
    - returns the (possibly still erroring) Response, or raises the last
    network exception if every attempt failed to connect at all. Retries
    are only attempted for RETRYABLE_STATUS_CODES / timeouts / transport
    errors; anything else (a 4xx that isn't 429, a successful response)
    returns immediately on the first attempt.

    `is_retryable` lets a caller override the default status-code check for
    a response body that signals a *permanent* condition despite a normally
    retryable status - e.g. Yahoo's 429 "AppID is denied: total count of
    AppID reached the URL's limit count" is a daily-quota exhaustion, not a
    transient rate limit, so retrying it can only waste attempts."""
    kwargs: dict = {"params": params, "timeout": timeout}
    if headers is not None:
        kwargs["headers"] = headers

    def _default_is_retryable(response: httpx.Response) -> bool:
        return response.status_code in RETRYABLE_STATUS_CODES

    should_retry = is_retryable or _default_is_retryable

    response: httpx.Response | None = None
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            response = httpx.get(url, **kwargs)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last_exc = exc
            response = None
        if response is not None and not should_retry(response):
            return response
        if attempt < max_retries:
            time.sleep(backoff_seconds * (attempt + 1))

    if response is not None:
        return response  # exhausted retries on a retryable status - let the caller's own error handling raise
    assert last_exc is not None
    raise last_exc
