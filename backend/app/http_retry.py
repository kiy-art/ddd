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
) -> httpx.Response:
    """Same contract as httpx.get(url, params=..., headers=..., timeout=...)
    - returns the (possibly still erroring) Response, or raises the last
    network exception if every attempt failed to connect at all. Retries
    are only attempted for RETRYABLE_STATUS_CODES / timeouts / transport
    errors; anything else (a 4xx that isn't 429, a successful response)
    returns immediately on the first attempt."""
    kwargs: dict = {"params": params, "timeout": timeout}
    if headers is not None:
        kwargs["headers"] = headers

    response: httpx.Response | None = None
    last_exc: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            response = httpx.get(url, **kwargs)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last_exc = exc
            response = None
        if response is not None and response.status_code not in RETRYABLE_STATUS_CODES:
            return response
        if attempt < max_retries:
            time.sleep(backoff_seconds * (attempt + 1))

    if response is not None:
        return response  # exhausted retries on a retryable status - let the caller's own error handling raise
    assert last_exc is not None
    raise last_exc
