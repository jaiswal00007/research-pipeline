import os
import httpx
from pipeline.http import http_get
from pipeline.models import RawSource, now_iso

_DEFAULT_SUBS = ["MachineLearning", "LocalLLaMA", "artificial", "singularity", "learnprogramming"]
_TOKEN_URL = "https://www.reddit.com/api/v1/access_token"


def _user_agent() -> str:
    return os.environ.get(
        "REDDIT_USER_AGENT",
        "python:ai-content-pipeline:v0.1 (by /u/ai_content_bot)",
    )


def _get_oauth_token(client_id: str, client_secret: str) -> str:
    resp = httpx.post(
        _TOKEN_URL,
        auth=(client_id, client_secret),
        data={"grant_type": "client_credentials"},
        headers={"User-Agent": _user_agent()},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def fetch_reddit_ai_posts(
    subreddits: list[str] | None = None,
    limit: int = 10,
) -> list[RawSource]:
    client_id = os.environ.get("REDDIT_CLIENT_ID")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("Reddit: REDDIT_CLIENT_ID/SECRET not set, skipping.")
        return []

    try:
        token = _get_oauth_token(client_id, client_secret)
    except Exception as exc:
        print(f"Reddit: failed to get OAuth token: {exc}")
        return []

    subs = subreddits or _DEFAULT_SUBS
    results: list[RawSource] = []
    seen: set[str] = set()

    for sub in subs:
        url = f"https://oauth.reddit.com/r/{sub}/hot"
        headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": _user_agent(),
        }
        try:
            resp = http_get(url, params={"limit": limit}, headers=headers, timeout=15)
        except httpx.HTTPStatusError as exc:
            print(f"Reddit: skipping r/{sub}: {exc.response.status_code}")
            continue
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
