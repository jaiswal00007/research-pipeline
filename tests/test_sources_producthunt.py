import httpx
import pytest
from pytest_httpx import HTTPXMock

from pipeline.sources.producthunt import fetch_producthunt_launches

_FEED_URL = "https://www.producthunt.com/feed"

SAMPLE_RSS = """\
<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Product Hunt</title>
    <item>
      <title>CodeAI - AI coding assistant for developers</title>
      <link>https://www.producthunt.com/posts/codeai</link>
      <description>An AI tool that helps developers write code faster.</description>
    </item>
    <item>
      <title>SomeCRMTool - Customer management</title>
      <link>https://www.producthunt.com/posts/somecrm</link>
      <description>Manage your customers better.</description>
    </item>
    <item>
      <title>LLM Playground - Test LLM models</title>
      <link>https://www.producthunt.com/posts/llm-playground</link>
      <description>Compare language models side by side.</description>
    </item>
  </channel>
</rss>
"""


def test_fetch_producthunt_returns_ai_only(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=_FEED_URL, text=SAMPLE_RSS)
    results = fetch_producthunt_launches()
    assert len(results) == 2
    titles = [r.title for r in results]
    assert "CodeAI - AI coding assistant for developers" in titles
    assert "LLM Playground - Test LLM models" in titles
    assert "SomeCRMTool - Customer management" not in titles


def test_fetch_producthunt_returns_rss_source_type(httpx_mock: HTTPXMock):
    httpx_mock.add_response(url=_FEED_URL, text=SAMPLE_RSS)
    results = fetch_producthunt_launches()
    assert all(r.source_type == "rss" for r in results)


def test_fetch_producthunt_handles_error(httpx_mock: HTTPXMock):
    # http_get retries ConnectError up to 3 times, so register 3 exceptions
    for _ in range(3):
        httpx_mock.add_exception(
            httpx.ConnectError("connection refused"),
            url=_FEED_URL,
        )
    results = fetch_producthunt_launches()
    assert results == []
