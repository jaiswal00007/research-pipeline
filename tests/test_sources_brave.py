import re
import pytest
from pytest_httpx import HTTPXMock
from pipeline.sources.brave import fetch_brave_search

_DDG_URL = "https://html.duckduckgo.com/html/"

# Minimal DDG HTML with 2 results
SAMPLE_HTML = """
<html><body>
<a class="result__a" href="https://example.com/1">AI Tool</a>
<span class="result__snippet">A useful AI development tool.</span>
<a class="result__a" href="https://example.com/2">Another AI Tool</a>
<span class="result__snippet">Another snippet.</span>
</body></html>
"""

EMPTY_HTML = "<html><body></body></html>"


def test_fetch_ddg_returns_sources(httpx_mock: HTTPXMock):
    # First query returns 2 results; remaining 4 return empty
    httpx_mock.add_response(url=_DDG_URL, text=SAMPLE_HTML)
    for _ in range(4):
        httpx_mock.add_response(url=_DDG_URL, text=EMPTY_HTML)

    results = fetch_brave_search()
    assert len(results) == 2
    assert all(r.source_type == "web" for r in results)
    assert results[0].url == "https://example.com/1"
    assert results[1].url == "https://example.com/2"


def test_fetch_ddg_deduplicates(httpx_mock: HTTPXMock):
    # All 5 queries return the same URL
    for _ in range(5):
        httpx_mock.add_response(url=_DDG_URL, text=SAMPLE_HTML)

    results = fetch_brave_search()
    assert len(results) == 2  # only 2 unique URLs across all 5 queries


def test_fetch_ddg_skips_failed_query(httpx_mock: HTTPXMock):
    # First query fails with 429, rest succeed with empty
    httpx_mock.add_response(url=_DDG_URL, status_code=429)
    for _ in range(4):
        httpx_mock.add_response(url=_DDG_URL, text=EMPTY_HTML)

    # Should not raise; failed query is skipped
    results = fetch_brave_search()
    assert isinstance(results, list)
