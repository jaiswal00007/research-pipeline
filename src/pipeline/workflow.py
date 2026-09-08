"""workflow.py — high-level orchestration for the social media pipeline."""
from __future__ import annotations

import os

from dotenv import load_dotenv

from pipeline.content.generator import CarouselGenerator
from pipeline.content.poster import InstagramPoster
from pipeline.db import get_db
from pipeline.runner import run_pipeline


def generate_content(db_conn=None, llm=None) -> list[dict]:
    """Generate carousel content for all approved topics that have no post yet."""
    conn = db_conn or get_db()

    rows = conn.execute(
        """
        SELECT t.id, t.title, t.summary
        FROM topics t
        WHERE t.status = 'approved'
          AND NOT EXISTS (SELECT 1 FROM posts p WHERE p.topic_id = t.id)
        """
    ).fetchall()

    results: list[dict] = []
    for row in rows:
        content = CarouselGenerator(llm=llm).generate(
            topic_id=row["id"],
            title=row["title"],
            summary=row["summary"],
            conn=conn,
        )
        results.append(content)

    print(f"Content generation complete. {len(results)} carousels saved.")
    return results


def post_approved(db_conn=None) -> list[str]:
    """Post all approved carousel posts to Instagram."""
    conn = db_conn or get_db()

    access_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
    account_id = os.environ.get("INSTAGRAM_ACCOUNT_ID")

    if not access_token or not account_id:
        print("Instagram credentials not configured. Skipping Instagram posts.")
        return []

    rows = conn.execute(
        "SELECT id, hook FROM posts WHERE status = 'approved' AND format = 'carousel'"
    ).fetchall()

    media_ids: list[str] = []
    for row in rows:
        try:
            poster = InstagramPoster(access_token=access_token, account_id=account_id)
            media_id = poster.post_carousel(
                post_id=row["id"],
                image_urls=[],
                caption=row["hook"] or "",
                conn=conn,
            )
            media_ids.append(media_id)
        except Exception as exc:
            print(f"Warning: failed to post post_id={row['id']}: {exc}")

    print(f"Posted {len(media_ids)} posts to Instagram.")
    return media_ids


def main() -> None:
    load_dotenv()
    print("=== Step 1: Running research pipeline ===")
    run_pipeline()
    print("\n=== Step 2: Generating content ===")
    generate_content()
    print("\nDone. Run `uv run approve` to review, then `uv run post` to publish.")
