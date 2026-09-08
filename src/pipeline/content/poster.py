from __future__ import annotations

import os
import sqlite3

import httpx

from pipeline.db import get_db
from pipeline.models import now_iso


class InstagramPoster:
    BASE_URL = "https://graph.facebook.com/v19.0"

    def __init__(self, access_token: str | None = None, account_id: str | None = None):
        self._token = access_token or os.environ.get("INSTAGRAM_ACCESS_TOKEN")
        self._account_id = account_id or os.environ.get("INSTAGRAM_ACCOUNT_ID")
        if not self._token or not self._account_id:
            raise ValueError(
                "INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_ACCOUNT_ID must be set "
                "(via env vars or constructor arguments)"
            )

    def post_carousel(
        self,
        post_id: int,
        image_urls: list[str],
        caption: str,
        conn: sqlite3.Connection | None = None,
    ) -> str:
        """Post a carousel to Instagram via the Graph API. Returns the media_id string."""
        if conn is None:
            conn = get_db()

        with httpx.Client() as client:
            # Step 1: Create a media container for each image
            item_ids: list[str] = []
            for image_url in image_urls:
                resp = client.post(
                    f"{self.BASE_URL}/{self._account_id}/media",
                    params={
                        "image_url": image_url,
                        "is_carousel_item": "true",
                        "access_token": self._token,
                    },
                )
                resp.raise_for_status()
                item_ids.append(resp.json()["id"])

            # Step 2: Create the carousel container
            resp = client.post(
                f"{self.BASE_URL}/{self._account_id}/media",
                params={
                    "media_type": "CAROUSEL",
                    "children": ",".join(item_ids),
                    "caption": caption,
                    "access_token": self._token,
                },
            )
            resp.raise_for_status()
            carousel_id = resp.json()["id"]

            # Step 3: Publish
            resp = client.post(
                f"{self.BASE_URL}/{self._account_id}/media_publish",
                params={
                    "creation_id": carousel_id,
                    "access_token": self._token,
                },
            )
            resp.raise_for_status()
            media_id = resp.json()["id"]

        # Step 4: Update the posts table
        now = now_iso()
        conn.execute(
            "UPDATE posts SET status='published', published_at=? WHERE id=?",
            (now, post_id),
        )

        # Step 5: Insert a platform_metrics row
        conn.execute(
            "INSERT INTO platform_metrics (post_id, platform, recorded_at) VALUES (?, 'instagram', ?)",
            (post_id, now),
        )
        conn.commit()

        return media_id


class YouTubePoster:
    BASE_URL = "https://www.googleapis.com/youtube/v3"

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or os.environ.get("YOUTUBE_API_KEY")
        if not self._api_key:
            raise ValueError(
                "YOUTUBE_API_KEY must be set (via env var or constructor argument)"
            )

    def post_community(
        self,
        title: str,
        summary: str,
        post_id: int | None = None,
        conn: sqlite3.Connection | None = None,
    ) -> str:
        """Post a YouTube Community post. Returns the YouTube post_id string."""
        with httpx.Client() as client:
            resp = client.post(
                f"{self.BASE_URL}/communityPosts",
                params={"key": self._api_key},
                json={
                    "snippet": {
                        "type": "textPost",
                        "textOriginalContent": f"{title}\n\n{summary}",
                    }
                },
            )
            resp.raise_for_status()
            yt_post_id = resp.json()["id"]

        if post_id is not None:
            if conn is None:
                conn = get_db()
            now = now_iso()
            conn.execute(
                "INSERT INTO platform_metrics (post_id, platform, recorded_at) VALUES (?, 'youtube', ?)",
                (post_id, now),
            )
            conn.commit()

        return yt_post_id
