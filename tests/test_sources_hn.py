import re
from pytest_httpx import HTTPXMock
from pipeline.sources.hackernews import fetch_hn_ai_stories

SAMPLE_HN = {
    "hits": [
        {
            "objectID": "12345",
            "title": "Show HN: Open-source AI coding assistant",
            "url": "https://example.com/ai-tool",
            "points": 300,
            "author": "dev123",
        }
    ]
}

def test_fetch_hn_stories_returns_sources(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=re.compile(r"https://hn\.algolia\.com/api/v1/search.*"),
        json=SAMPLE_HN,
    )
    results = fetch_hn_ai_stories(min_points=100)
    assert len(results) == 1
    assert results[0].source_type == "hackernews"
    assert results[0].title == "Show HN: Open-source AI coding assistant"

def test_fetch_hn_filters_low_points(httpx_mock: HTTPXMock):
    low_points = {"hits": [{"objectID": "1", "title": "Meh", "url": "https://x.com", "points": 5, "author": "x"}]}
    httpx_mock.add_response(
        url=re.compile(r"https://hn\.algolia\.com/api/v1/search.*"),
        json=low_points,
    )
    results = fetch_hn_ai_stories(min_points=100)
    assert results == []
