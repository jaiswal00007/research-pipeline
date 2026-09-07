import os
from datetime import datetime, timezone
import httpx
from pipeline.models import RawSource

_BASE = "https://api.github.com"
_AI_QUERIES = [
    "AI coding agent",
    "LLM developer tool",
    "local AI assistant",
    "open source AI workflow",
]


def _headers(token: str | None) -> dict[str, str]:
    h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    t = token or os.environ.get("GITHUB_TOKEN")
    if t:
        h["Authorization"] = f"Bearer {t}"
    return h


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def search_github_ai(query: str, token: str | None = None) -> list[RawSource]:
    params = {"q": f"{query} language:Python stars:>50", "sort": "stars", "per_page": 10}
    resp = httpx.get(f"{_BASE}/search/repositories", params=params, headers=_headers(token), timeout=15)
    resp.raise_for_status()
    items = resp.json().get("items", [])
    return [
        RawSource(
            url=item["html_url"],
            title=item["full_name"],
            source_type="github",
            fetched_at=_now(),
            raw=item,
        )
        for item in items
    ]


def fetch_github_trending(token: str | None = None) -> list[RawSource]:
    all_results: list[RawSource] = []
    for q in _AI_QUERIES:
        all_results.extend(search_github_ai(q, token=token))
    seen: set[str] = set()
    unique = []
    for s in all_results:
        if s.url not in seen:
            seen.add(s.url)
            unique.append(s)
    return unique
