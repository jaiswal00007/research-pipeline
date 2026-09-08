import re

import pytest
from pytest_httpx import HTTPXMock

from pipeline.sources.arxiv import fetch_arxiv_papers, _SEARCHES

_ARXIV_URL_PATTERN = re.compile(r"http://export\.arxiv\.org/api/query.*")

SAMPLE_ATOM = """\
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2401.00001v1</id>
    <title>Advances in Large Language Models</title>
    <summary>We present a new approach to LLM training.</summary>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2401.00002v1</id>
    <title>Efficient Neural Architecture Search</title>
    <summary>A faster method for NAS.</summary>
  </entry>
</feed>
"""

EMPTY_ATOM = """\
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
</feed>
"""


def test_fetch_arxiv_returns_sources(httpx_mock: HTTPXMock):
    # Register a response for each of the 3 category searches
    httpx_mock.add_response(url=_ARXIV_URL_PATTERN, text=SAMPLE_ATOM)
    httpx_mock.add_response(url=_ARXIV_URL_PATTERN, text=EMPTY_ATOM)
    httpx_mock.add_response(url=_ARXIV_URL_PATTERN, text=EMPTY_ATOM)

    results = fetch_arxiv_papers(max_results=5)

    assert len(results) >= 2
    assert all(r.source_type == "rss" for r in results)
    urls = [r.url for r in results]
    assert "http://arxiv.org/abs/2401.00001v1" in urls
    assert "http://arxiv.org/abs/2401.00002v1" in urls


def test_fetch_arxiv_deduplicates(httpx_mock: HTTPXMock):
    # All 3 category searches return the same paper IDs
    for _ in range(len(_SEARCHES)):
        httpx_mock.add_response(url=_ARXIV_URL_PATTERN, text=SAMPLE_ATOM)

    results = fetch_arxiv_papers(max_results=5)

    # 2 unique papers despite 3 searches each returning the same 2
    assert len(results) == 2
    urls = [r.url for r in results]
    assert len(urls) == len(set(urls))


def test_fetch_arxiv_skips_failed_category(httpx_mock: HTTPXMock):
    # Use a 404 (not retried by http_get) so only one mock call needed for the failure
    httpx_mock.add_response(url=_ARXIV_URL_PATTERN, status_code=404)
    httpx_mock.add_response(url=_ARXIV_URL_PATTERN, text=SAMPLE_ATOM)
    httpx_mock.add_response(url=_ARXIV_URL_PATTERN, text=SAMPLE_ATOM)

    # Should not raise; should return results from the two successful calls
    results = fetch_arxiv_papers(max_results=5)
    assert len(results) >= 2
    assert all(r.source_type == "rss" for r in results)
