import pytest
from pytest_httpx import HTTPXMock

from pipeline.sources.rss import fetch_rss_feeds

SAMPLE_RSS = """\
<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Test Blog</title>
    <item>
      <title>New AI Model Released</title>
      <link>https://example.com/post-1</link>
      <description>A new model dropped today.</description>
    </item>
    <item>
      <title>Second Post</title>
      <link>https://example.com/post-2</link>
      <description>Another post.</description>
    </item>
  </channel>
</rss>
"""


def _make_feed_xml(n: int) -> str:
    items = "".join(
        f"""
    <item>
      <title>Post {i}</title>
      <link>https://example.com/post-{i}</link>
      <description>Description {i}.</description>
    </item>"""
        for i in range(1, n + 1)
    )
    return f'<?xml version="1.0"?><rss version="2.0"><channel>{items}</channel></rss>'


def test_fetch_rss_returns_sources(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://example.com/feed.xml",
        text=SAMPLE_RSS,
    )
    results = fetch_rss_feeds(feeds=[("Test Blog", "https://example.com/feed.xml")])
    assert len(results) == 2
    assert all(r.source_type == "rss" for r in results)
    assert results[0].title == "New AI Model Released"
    assert results[1].title == "Second Post"


def test_fetch_rss_limits_to_five_items(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://example.com/feed.xml",
        text=_make_feed_xml(7),
    )
    results = fetch_rss_feeds(feeds=[("Big Feed", "https://example.com/feed.xml")])
    assert len(results) == 5


def test_fetch_rss_skips_failed_feed(httpx_mock: HTTPXMock):
    # Use a 404 response which raises HTTPStatusError (non-retried) so only one mock call needed
    httpx_mock.add_response(
        url="https://example.com/bad-feed.xml",
        status_code=404,
    )
    httpx_mock.add_response(
        url="https://example.com/good-feed.xml",
        text=SAMPLE_RSS,
    )
    results = fetch_rss_feeds(feeds=[
        ("Bad Feed", "https://example.com/bad-feed.xml"),
        ("Good Feed", "https://example.com/good-feed.xml"),
    ])
    assert len(results) == 2
    assert all(r.source_type == "rss" for r in results)


def test_fetch_rss_deduplicates(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://example.com/feed-a.xml",
        text=SAMPLE_RSS,
    )
    httpx_mock.add_response(
        url="https://example.com/feed-b.xml",
        text=SAMPLE_RSS,
    )
    results = fetch_rss_feeds(feeds=[
        ("Feed A", "https://example.com/feed-a.xml"),
        ("Feed B", "https://example.com/feed-b.xml"),
    ])
    urls = [r.url for r in results]
    assert len(urls) == len(set(urls)), "URLs should be deduplicated"
    assert len(results) == 2
