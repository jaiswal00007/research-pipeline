import xml.etree.ElementTree as ET

from pipeline.http import http_get
from pipeline.models import RawSource, now_iso

_FEED_URL = "https://www.producthunt.com/feed"
_AI_KEYWORDS = [
    "ai", "ml", "machine learning", "llm", "gpt", "claude",
    "developer", "coding", "automation", "agent",
]


def fetch_producthunt_launches() -> list[RawSource]:
    try:
        resp = http_get(_FEED_URL, timeout=15)
        root = ET.fromstring(resp.text)
        results: list[RawSource] = []
        for item in root.findall(".//item"):
            title = item.findtext("title") or ""
            link = item.findtext("link") or ""
            description = item.findtext("description") or ""
            if not link:
                continue
            haystack = (title + " " + description).lower()
            if not any(kw in haystack for kw in _AI_KEYWORDS):
                continue
            results.append(RawSource(
                url=link,
                title=title,
                source_type="rss",
                fetched_at=now_iso(),
                raw={"description": description, "source": "producthunt"},
            ))
            if len(results) >= 20:
                break
        return results
    except Exception as exc:
        print(f"Product Hunt: failed to fetch: {exc}")
        return []
