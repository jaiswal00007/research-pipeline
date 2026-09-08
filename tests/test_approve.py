# tests/test_approve.py
import json
import sqlite3
from unittest.mock import patch

import pytest

from pipeline.cli.approve import ApprovalCLI, main
from pipeline.models import now_iso


def _insert_topic(db, title="Test Topic", score_total=42.0):
    cur = db.execute(
        "INSERT INTO topics (title, score_total, created_at) VALUES (?, ?, ?)",
        (title, score_total, now_iso()),
    )
    db.commit()
    return cur.lastrowid


def _insert_post(db, topic_id, status="pending_approval", content_json=None):
    if content_json is None:
        content = {
            "slides": [{"slide": i, "title": f"Title {i}", "body": f"Body {i}"} for i in range(1, 11)],
            "caption": "Test caption",
            "hashtags": ["#test"],
        }
        content_json = json.dumps(content)
    cur = db.execute(
        "INSERT INTO posts (topic_id, format, hook, content_json, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (topic_id, "carousel", "Hook text", content_json, status, now_iso()),
    )
    db.commit()
    return cur.lastrowid


# --- Tests ---


def test_get_pending_posts_returns_pending(db):
    topic_id = _insert_topic(db, title="AI Tools", score_total=85.5)
    post_id = _insert_post(db, topic_id, status="pending_approval")

    cli = ApprovalCLI(conn=db)
    posts = cli.get_pending_posts()

    assert len(posts) == 1
    p = posts[0]
    assert p["id"] == post_id
    assert p["topic_id"] == topic_id
    assert p["topic_title"] == "AI Tools"
    assert p["score_total"] == 85.5
    assert p["hook"] == "Hook text"
    assert p["format"] == "carousel"
    assert "content_json" in p
    assert "created_at" in p


def test_get_pending_posts_excludes_non_pending(db):
    topic_id = _insert_topic(db)
    _insert_post(db, topic_id, status="approved")
    _insert_post(db, topic_id, status="draft")

    cli = ApprovalCLI(conn=db)
    posts = cli.get_pending_posts()

    assert posts == []


def test_approve_sets_status(db):
    topic_id = _insert_topic(db)
    post_id = _insert_post(db, topic_id, status="pending_approval")

    cli = ApprovalCLI(conn=db)
    cli.approve(post_id)

    row = db.execute("SELECT status FROM posts WHERE id = ?", (post_id,)).fetchone()
    assert row["status"] == "approved"


def test_reject_sets_status(db):
    topic_id = _insert_topic(db)
    post_id = _insert_post(db, topic_id, status="pending_approval")

    cli = ApprovalCLI(conn=db)
    cli.reject(post_id)

    row = db.execute("SELECT status FROM posts WHERE id = ?", (post_id,)).fetchone()
    assert row["status"] == "rejected"


def test_main_no_pending_prints_message(db, capsys):
    # No posts inserted — nothing pending
    with patch("pipeline.cli.approve.get_db", return_value=db):
        main()

    captured = capsys.readouterr()
    assert "No posts pending approval." in captured.out
