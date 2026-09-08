import xml.etree.ElementTree as ET

from pipeline.http import http_get
from pipeline.models import RawSource, now_iso

_ARXIV_API = "https://export.arxiv.org/api/query"
_NS = {"atom": "http://www.w3.org/2005/Atom"}

_SEARCHES = [
    "cat:cs.AI",   # AI
    "cat:cs.LG",   # Machine Learning
    "cat:cs.CL",   # Computation and Language (NLP/LLMs)
]


def fetch_arxiv_papers(max_results: int = 10) -> list[RawSource]:
    seen: set[str] = set()
    results: list[RawSource] = []

    for search in _SEARCHES:
        try:
            params = {
                "search_query": search,
                "start": 0,
                "max_results": max_results,
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            }
            resp = http_get(_ARXIV_API, params=params, timeout=20)
            root = ET.fromstring(resp.text)
            entries = root.findall("atom:entry", _NS)
            for entry in entries:
                url = entry.findtext("atom:id", "", _NS).strip()
                title = entry.findtext("atom:title", "", _NS).strip()
                summary = entry.findtext("atom:summary", "", _NS).strip()
                if not url or url in seen:
                    continue
                seen.add(url)
                results.append(
                    RawSource(
                        url=url,
                        title=title,
                        source_type="rss",
                        fetched_at=now_iso(),
                        raw={"summary": summary, "category": search},
                    )
                )
        except Exception as exc:
            print(f"arXiv: failed to fetch {search}: {exc}")
            continue

    return results
