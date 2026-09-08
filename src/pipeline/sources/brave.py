from __future__ import annotations

import os

from pipeline.http import http_get
from pipeline.models import RawSource, now_iso

_BASE_URL = "https://api.search.brave.com/res/v1/web/search"

_QUERIES = [
    "new AI tools for developers 2026",
    "open source LLM release 2026",
    "AI coding assistant developer workflow",
    "agentic AI framework Python",
    "local AI model developer tool",
]


def fetch_brave_search(api_key: str | None = None) -> list[RawSource]:
    if api_key is None:
        api_key = os.environ.get("BRAVE_API_KEY")
    if not api_key:
        print("Brave Search: BRAVE_API_KEY not set, skipping.")
        return []

    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": api_key,
    }

    seen_urls: set[str] = set()
    results: list[RawSource] = []

    for query in _QUERIES:
        params = {"q": query, "count": 10, "freshness": "pd"}
        resp = http_get(_BASE_URL, params=params, headers=headers, timeout=15)
        web_results = resp.json().get("web", {}).get("results", [])
        for item in web_results:
            url = item.get("url", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            results.append(RawSource(
                url=url,
                title=item.get("title", ""),
                source_type="web",
                fetched_at=now_iso(),
                raw=item,
            ))

    return results
