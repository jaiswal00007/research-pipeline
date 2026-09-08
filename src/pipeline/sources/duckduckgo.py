from __future__ import annotations

import re

import httpx

from pipeline.models import RawSource, now_iso

_DDG_URL = "https://html.duckduckgo.com/html/"

_QUERIES = [
    "new AI tools for developers 2026",
    "open source LLM release 2026",
    "AI coding assistant developer workflow",
    "agentic AI framework Python",
    "local AI model developer tool",
]

_LINK_RE = re.compile(r'class="result__a"[^>]*href="([^"]+)"[^>]*>([^<]+)<')
_SNIPPET_RE = re.compile(r'class="result__snippet"[^>]*>([^<]+)<')


def fetch_brave_search(api_key: str | None = None) -> list[RawSource]:
    """Fetch AI-related web results via DuckDuckGo HTML search (free, no key needed)."""
    seen_urls: set[str] = set()
    results: list[RawSource] = []

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }

    for query in _QUERIES:
        try:
            resp = httpx.post(
                _DDG_URL,
                data={"q": query, "kl": "us-en"},
                headers=headers,
                timeout=15,
                follow_redirects=True,
            )
            resp.raise_for_status()
            html = resp.text

            links = _LINK_RE.findall(html)
            snippets = _SNIPPET_RE.findall(html)

            for i, (url, title) in enumerate(links[:10]):
                if not url or url in seen_urls:
                    continue
                if url.startswith("//duckduckgo.com") or url.startswith("/?"):
                    continue
                seen_urls.add(url)
                snippet = snippets[i] if i < len(snippets) else ""
                results.append(RawSource(
                    url=url,
                    title=title.strip(),
                    source_type="web",
                    fetched_at=now_iso(),
                    raw={"snippet": snippet, "query": query},
                ))
        except Exception as exc:
            print(f"DuckDuckGo search failed for '{query}': {exc}")
            continue

    return results
