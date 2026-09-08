import json
import sqlite3

from dotenv import load_dotenv

from pipeline.db import get_db


class ApprovalCLI:
    def __init__(self, conn=None):
        self.conn = conn if conn is not None else get_db()

    def get_pending_posts(self) -> list[dict]:
        rows = self.conn.execute(
            """
            SELECT
                p.id,
                p.topic_id,
                t.title  AS topic_title,
                t.score_total,
                t.score_usefulness,
                t.score_novelty,
                t.score_dev_value,
                t.score_search_demand,
                t.score_monetization,
                t.score_ease_demo,
                p.hook,
                p.content_json,
                p.format,
                p.created_at
            FROM posts p
            JOIN topics t ON t.id = p.topic_id
            WHERE p.status = 'pending_approval'
            ORDER BY p.created_at
            """
        ).fetchall()
        return [dict(row) for row in rows]

    def approve(self, post_id: int) -> None:
        self.conn.execute(
            "UPDATE posts SET status = 'approved' WHERE id = ?",
            (post_id,),
        )
        self.conn.commit()

    def reject(self, post_id: int) -> None:
        self.conn.execute(
            "UPDATE posts SET status = 'rejected' WHERE id = ?",
            (post_id,),
        )
        self.conn.commit()


def main() -> None:
    load_dotenv()

    cli = ApprovalCLI()
    posts = cli.get_pending_posts()

    if not posts:
        print("No posts pending approval.")
        return

    total = len(posts)
    for i, post in enumerate(posts, start=1):
        topic_title = post["topic_title"]
        score_total = post["score_total"] or 0.0
        print(f"\n=== Post {i}/{total}: {topic_title} (score: {score_total:.0f}) ===")
        print(
            f"Scores: "
            f"usefulness={post['score_usefulness'] or 0:.0f} "
            f"novelty={post['score_novelty'] or 0:.0f} "
            f"dev_value={post['score_dev_value'] or 0:.0f} "
            f"search_demand={post['score_search_demand'] or 0:.0f} "
            f"monetization={post['score_monetization'] or 0:.0f} "
            f"ease_demo={post['score_ease_demo'] or 0:.0f} "
            f"| total={score_total:.0f}"
        )

        try:
            content = json.loads(post["content_json"])
        except (json.JSONDecodeError, TypeError):
            content = {}

        for slide in content.get("slides", []):
            n = slide.get("slide", "?")
            title = slide.get("title", "")
            body = slide.get("body", "")
            print(f"[Slide {n}] {title}\n{body}\n")

        caption = content.get("caption", "")
        hashtags = content.get("hashtags", [])
        print(f"Caption: {caption}")
        print(f"Hashtags: {' '.join(hashtags)}")

        choice = input("[a]pprove / [r]eject / [s]kip / [q]uit: ").strip().lower()

        if choice == "a":
            cli.approve(post["id"])
            print("Approved.")
        elif choice == "r":
            cli.reject(post["id"])
            print("Rejected.")
        elif choice == "s":
            print("Skipped.")
        elif choice == "q":
            print("Quitting.")
            return
        else:
            print("Unknown key, skipping.")
