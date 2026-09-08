import re
import pytest
from pytest_httpx import HTTPXMock
from pipeline.sources.brave import fetch_brave_search

_BRAVE_URL_PATTERN = re.compile(r"https://api\.search\.brave\.com/res/v1/web/search.*")

SAMPLE_RESPONSE_1 = {
    "web": {
        "results": [
            {"url": "https://example.com/1", "title": "AI Tool", "description": "desc"},
            {"url": "https://example.com/2", "title": "Another AI Tool", "description": "desc2"},
        ]
    }
}

SAMPLE_RESPONSE_SINGLE = {
    "web": {
        "results": [
            {"url": "https://example.com/1", "title": "AI Tool", "description": "desc"}
        ]
    }
}

EMPTY_RESPONSE = {"web": {"results": []}}


def test_fetch_brave_returns_sources(httpx_mock: HTTPXMock):
    # Only mock 1 query (the first one) with 2 results; remaining queries return empty
    httpx_mock.add_response(
        url=_BRAVE_URL_PATTERN,
        json=SAMPLE_RESPONSE_1,
    )
    for _ in range(4):
        httpx_mock.add_response(
            url=_BRAVE_URL_PATTERN,
            json=EMPTY_RESPONSE,
        )

    results = fetch_brave_search(api_key="test-key")
    assert len(results) == 2
    assert all(r.source_type == "web" for r in results)
    assert results[0].url == "https://example.com/1"
    assert results[1].url == "https://example.com/2"


def test_fetch_brave_skips_without_key(monkeypatch):
    monkeypatch.delenv("BRAVE_API_KEY", raising=False)
    results = fetch_brave_search(api_key=None)
    assert results == []


def test_fetch_brave_deduplicates(httpx_mock: HTTPXMock):
    # All 5 queries return the same URL
    for _ in range(5):
        httpx_mock.add_response(
            url=_BRAVE_URL_PATTERN,
            json=SAMPLE_RESPONSE_SINGLE,
        )

    results = fetch_brave_search(api_key="test-key")
    assert len(results) == 1
    assert results[0].url == "https://example.com/1"
