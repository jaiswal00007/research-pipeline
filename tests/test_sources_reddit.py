import re
import pytest
from pytest_httpx import HTTPXMock
from pipeline.sources.reddit import fetch_reddit_ai_posts

_TOKEN_URL = re.compile(r"https://www\.reddit\.com/api/v1/access_token.*")
_OAUTH_URL = re.compile(r"https://oauth\.reddit\.com/r/.*")

SAMPLE_TOKEN = {"access_token": "fake_token", "token_type": "bearer"}

SAMPLE_REDDIT = {
    "data": {
        "children": [
            {"data": {
                "id": "abc123",
                "title": "New open source AI coding tool",
                "url": "https://github.com/foo/bar",
                "permalink": "/r/MachineLearning/comments/abc123/",
                "score": 500,
                "selftext": "Check out this tool",
            }}
        ]
    }
}

SAMPLE_REDDIT_2 = {
    "data": {
        "children": [
            {"data": {
                "id": "xyz789",
                "title": "Running LLMs locally",
                "url": "https://github.com/different/repo",
                "permalink": "/r/LocalLLaMA/comments/xyz789/",
                "score": 350,
                "selftext": "Local LLM guide",
            }}
        ]
    }
}


def test_fetch_reddit_posts(httpx_mock: HTTPXMock, monkeypatch):
    monkeypatch.setenv("REDDIT_CLIENT_ID", "test_id")
    monkeypatch.setenv("REDDIT_CLIENT_SECRET", "test_secret")
    httpx_mock.add_response(url=_TOKEN_URL, json=SAMPLE_TOKEN)
    httpx_mock.add_response(url=_OAUTH_URL, json=SAMPLE_REDDIT)
    results = fetch_reddit_ai_posts(["MachineLearning"], limit=5)
    assert len(results) == 1
    assert results[0].source_type == "reddit"
    assert results[0].title == "New open source AI coding tool"


def test_fetch_reddit_multiple_subreddits(httpx_mock: HTTPXMock, monkeypatch):
    monkeypatch.setenv("REDDIT_CLIENT_ID", "test_id")
    monkeypatch.setenv("REDDIT_CLIENT_SECRET", "test_secret")
    httpx_mock.add_response(url=_TOKEN_URL, json=SAMPLE_TOKEN)
    httpx_mock.add_response(url=re.compile(r"https://oauth\.reddit\.com/r/MachineLearning/.*"), json=SAMPLE_REDDIT)
    httpx_mock.add_response(url=re.compile(r"https://oauth\.reddit\.com/r/LocalLLaMA/.*"), json=SAMPLE_REDDIT_2)
    results = fetch_reddit_ai_posts(["MachineLearning", "LocalLLaMA"], limit=5)
    assert len(results) == 2


def test_fetch_reddit_skips_without_credentials(monkeypatch):
    monkeypatch.delenv("REDDIT_CLIENT_ID", raising=False)
    monkeypatch.delenv("REDDIT_CLIENT_SECRET", raising=False)
    results = fetch_reddit_ai_posts()
    assert results == []
