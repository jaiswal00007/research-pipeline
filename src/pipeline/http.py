import time
import httpx

_RETRY_STATUSES = {429, 503}
_MAX_ATTEMPTS = 3


def http_get(url: str, *, params=None, headers=None, timeout: int = 30) -> httpx.Response:
    """GET with 3 attempts, exponential backoff on 429/503/connection errors."""
    last_exc: Exception | None = None
    for attempt in range(_MAX_ATTEMPTS):
        try:
            resp = httpx.get(url, params=params, headers=headers, timeout=timeout, follow_redirects=True)
            resp.raise_for_status()
            return resp
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in _RETRY_STATUSES:
                last_exc = exc
                time.sleep(2 ** attempt)
            else:
                raise
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            last_exc = exc
            time.sleep(2 ** attempt)
    assert last_exc is not None
    raise last_exc


def http_post(url: str, *, params=None, json=None, timeout: int = 30) -> httpx.Response:
    """POST with 3 attempts, exponential backoff on 429/503/connection errors."""
    last_exc: Exception | None = None
    for attempt in range(_MAX_ATTEMPTS):
        try:
            resp = httpx.post(url, params=params, json=json, timeout=timeout)
            resp.raise_for_status()
            return resp
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in _RETRY_STATUSES:
                last_exc = exc
                time.sleep(2 ** attempt)
            else:
                raise
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            last_exc = exc
            time.sleep(2 ** attempt)
    assert last_exc is not None
    raise last_exc
