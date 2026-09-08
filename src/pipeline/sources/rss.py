import xml.etree.ElementTree as ET

from pipeline.http import http_get
from pipeline.models import RawSource, now_iso

_FEEDS = [
    ("OpenAI News", "https://openai.com/news/rss.xml"),
    ("Anthropic News", "https://www.anthropic.com/feed.rss"),
    ("Google DeepMind Blog", "https://deepmind.google/blog/rss.xml"),
    ("Mistral AI Blog", "https://mistral.ai/news/rss"),
    ("Hugging Face Blog", "https://huggingface.co/blog/feed.xml"),
]


def fetch_rss_feeds(feeds=None) -> list[RawSource]:
    if feeds is None:
        feeds = _FEEDS

    seen_urls: set[str] = set()
    results: list[RawSource] = []

    for name, url in feeds:
        try:
            resp = http_get(url, timeout=15)
            root = ET.fromstring(resp.text)
            items = root.findall(".//item")
            count = 0
            for item in items:
                if count >= 5:
                    break
                link = item.findtext("link") or ""
                if not link:
                    continue
                if link in seen_urls:
                    continue
                seen_urls.add(link)
                title = item.findtext("title") or ""
                description = item.findtext("description") or ""
                results.append(RawSource(
                    url=link,
                    title=title,
                    source_type="rss",
                    fetched_at=now_iso(),
                    raw={"feed_name": name, "description": description},
                ))
                count += 1
        except Exception as exc:
            print(f"RSS: failed to fetch {name}: {exc}")
            continue

    return results
