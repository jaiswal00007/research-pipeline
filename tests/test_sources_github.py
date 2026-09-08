import pytest
import re
from pytest_httpx import HTTPXMock
from pipeline.sources.github import fetch_github_trending, search_github_ai

SAMPLE_SEARCH_RESPONSE = {
    "items": [
        {
            "full_name": "owner/cool-ai-tool",
            "html_url": "https://github.com/owner/cool-ai-tool",
            "description": "A cool AI tool",
            "stargazers_count": 1200,
            "language": "Python",
            "license": {"spdx_id": "MIT"},
        }
    ]
}

def test_search_github_ai_returns_sources(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=re.compile(r"https://api\.github\.com/search/repositories.*"),
        json=SAMPLE_SEARCH_RESPONSE,
    )
    results = search_github_ai("AI coding agent", token=None)
    assert len(results) == 1
    assert results[0].source_type == "github"
    assert results[0].url == "https://github.com/owner/cool-ai-tool"
    assert results[0].title == "owner/cool-ai-tool"

def test_search_github_ai_sets_fetched_at(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url=re.compile(r"https://api\.github\.com/search/repositories.*"),
        json=SAMPLE_SEARCH_RESPONSE,
    )
    results = search_github_ai("AI", token=None)
    assert results[0].fetched_at  # non-empty ISO string
