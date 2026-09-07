from datetime import datetime, timezone
import httpx
from pipeline.models import RawSource

_ALGOLIA = "https://hn.algolia.com/api/v1/search"
_AI_TAGS = ["AI", "LLM", "machine learning", "open source AI", "coding agent"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def fetch_hn_ai_stories(min_points: int = 100) -> list[RawSource]:
    query = " OR ".join(_AI_TAGS)
    params = {
        "query": query,
        "tags": "story",
        "hitsPerPage": 30,
        "numericFilters": f"points>{min_points}",
    }
    resp = httpx.get(_ALGOLIA, params=params, timeout=15)
    resp.raise_for_status()
    hits = resp.json().get("hits", [])
    results = []
    for hit in hits:
        if hit.get("points", 0) <= min_points:
            continue
        url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit['objectID']}"
        results.append(RawSource(
            url=url,
            title=hit.get("title", ""),
            source_type="hackernews",
            fetched_at=_now(),
            raw=hit,
        ))
    return results
