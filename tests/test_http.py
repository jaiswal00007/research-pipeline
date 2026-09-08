"""Tests for pipeline.http retry logic."""
from unittest.mock import patch

import httpx
import pytest

from pipeline.http import http_get, http_post


def test_http_get_success(httpx_mock):
    httpx_mock.add_response(method="GET", url="https://example.com/api", status_code=200)

    with patch("pipeline.http.time.sleep") as mock_sleep:
        resp = http_get("https://example.com/api")

    assert resp.status_code == 200
    mock_sleep.assert_not_called()


def test_http_get_retries_on_429(httpx_mock):
    httpx_mock.add_response(method="GET", url="https://example.com/api", status_code=429)
    httpx_mock.add_response(method="GET", url="https://example.com/api", status_code=200)

    with patch("pipeline.http.time.sleep") as mock_sleep:
        resp = http_get("https://example.com/api")

    assert resp.status_code == 200
    assert len(httpx_mock.get_requests()) == 2
    mock_sleep.assert_called_once_with(1)  # 2**0 = 1


def test_http_get_raises_after_max_retries(httpx_mock):
    httpx_mock.add_response(method="GET", url="https://example.com/api", status_code=429)
    httpx_mock.add_response(method="GET", url="https://example.com/api", status_code=429)
    httpx_mock.add_response(method="GET", url="https://example.com/api", status_code=429)

    with patch("pipeline.http.time.sleep"):
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            http_get("https://example.com/api")

    assert exc_info.value.response.status_code == 429
    assert len(httpx_mock.get_requests()) == 3


def test_http_post_success(httpx_mock):
    httpx_mock.add_response(method="POST", url="https://example.com/api", status_code=200)

    with patch("pipeline.http.time.sleep") as mock_sleep:
        resp = http_post("https://example.com/api", json={"key": "value"})

    assert resp.status_code == 200
    mock_sleep.assert_not_called()


def test_http_get_raises_immediately_on_404(httpx_mock):
    httpx_mock.add_response(method="GET", url="https://example.com/api", status_code=404)

    with patch("pipeline.http.time.sleep") as mock_sleep:
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            http_get("https://example.com/api")

    assert exc_info.value.response.status_code == 404
    # Only 1 request should have been made — no retries for 404
    assert len(httpx_mock.get_requests()) == 1
    mock_sleep.assert_not_called()
