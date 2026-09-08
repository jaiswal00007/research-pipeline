# tests/test_workflow.py
import os
from unittest.mock import patch

import pytest

from pipeline.workflow import generate_content, post_approved


def test_generate_content_calls_generator_for_approved_topics(db):
    db.execute(
        "INSERT INTO topics (title, summary, status, created_at) VALUES (?, ?, ?, ?)",
        ("Test Topic", "A summary", "approved", "2026-01-01T00:00:00"),
    )
    db.commit()

    fake_result = {"slides": [], "caption": "", "hashtags": []}
    with patch(
        "pipeline.content.generator.CarouselGenerator.generate",
        return_value=fake_result,
    ) as mock_gen:
        result = generate_content(db_conn=db)

    mock_gen.assert_called_once()
    assert result == [fake_result]


def test_generate_content_skips_topics_with_existing_post(db):
    db.execute(
        "INSERT INTO topics (title, summary, status, created_at) VALUES (?, ?, ?, ?)",
        ("Test Topic", "A summary", "approved", "2026-01-01T00:00:00"),
    )
    db.execute(
        "INSERT INTO posts (topic_id, format, hook, content_json, status, created_at) "
        "VALUES (1, 'carousel', 'hook', '{}', 'pending_approval', '2026-01-01T00:00:00')"
    )
    db.commit()

    with patch(
        "pipeline.content.generator.CarouselGenerator.generate",
    ) as mock_gen:
        generate_content(db_conn=db)

    mock_gen.assert_not_called()


def test_generate_content_skips_pending_topics(db):
    db.execute(
        "INSERT INTO topics (title, summary, status, created_at) VALUES (?, ?, ?, ?)",
        ("Test Topic", "A summary", "pending", "2026-01-01T00:00:00"),
    )
    db.commit()

    with patch(
        "pipeline.content.generator.CarouselGenerator.generate",
    ) as mock_gen:
        generate_content(db_conn=db)

    mock_gen.assert_not_called()


def test_post_approved_skips_if_no_credentials(db, monkeypatch):
    monkeypatch.delenv("INSTAGRAM_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("INSTAGRAM_ACCOUNT_ID", raising=False)

    result = post_approved(db_conn=db)

    assert result == []


def test_post_approved_posts_approved_carousel(db, monkeypatch):
    db.execute(
        "INSERT INTO topics (title, summary, status, created_at) VALUES (?, ?, ?, ?)",
        ("Test Topic", "A summary", "approved", "2026-01-01T00:00:00"),
    )
    db.execute(
        "INSERT INTO posts (topic_id, format, hook, content_json, status, created_at) "
        "VALUES (1, 'carousel', 'hook', '{}', 'approved', '2026-01-01T00:00:00')"
    )
    db.commit()

    monkeypatch.setenv("INSTAGRAM_ACCESS_TOKEN", "test_token")
    monkeypatch.setenv("INSTAGRAM_ACCOUNT_ID", "test_account")

    with patch(
        "pipeline.content.poster.InstagramPoster.post_carousel",
        return_value="media123",
    ):
        result = post_approved(db_conn=db)

    assert result == ["media123"]
