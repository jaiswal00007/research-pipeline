import os
import httpx
from pipeline.models import RawSource, now_iso

_DEFAULT_SUBS = ["MachineLearning", "LocalLLaMA", "artificial", "singularity", "Programming"]


def _user_agent() -> str:
    return os.environ.get("REDDIT_USER_AGENT", "pipeline/0.1")


def fetch_reddit_ai_posts(
    subreddits: list[str] | None = None,
    limit: int = 10,
) -> list[RawSource]:
    subs = subreddits or _DEFAULT_SUBS
    results: list[RawSource] = []
    seen: set[str] = set()

    for sub in subs:
        url = f"https://www.reddit.com/r/{sub}/hot.json"
        headers = {"User-Agent": _user_agent()}
        resp = httpx.get(url, params={"limit": limit}, headers=headers, timeout=15)
        resp.raise_for_status()
        children = resp.json().get("data", {}).get("children", [])
        for child in children:
            post = child["data"]
            post_url = post.get("url", f"https://reddit.com{post.get('permalink', '')}")
            if post_url in seen:
                continue
            seen.add(post_url)
            results.append(RawSource(
                url=post_url,
                title=post.get("title", ""),
                source_type="reddit",
                fetched_at=now_iso(),
                raw=post,
            ))
    return results
