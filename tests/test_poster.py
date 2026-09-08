import pytest
from pipeline.content.poster import InstagramPoster, YouTubePoster


# ---------------------------------------------------------------------------
# InstagramPoster tests
# ---------------------------------------------------------------------------

def test_instagram_raises_without_token(monkeypatch):
    monkeypatch.delenv("INSTAGRAM_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("INSTAGRAM_ACCOUNT_ID", raising=False)
    with pytest.raises(ValueError):
        InstagramPoster()


def test_instagram_post_carousel_success(httpx_mock, db, monkeypatch):
    monkeypatch.setenv("INSTAGRAM_ACCESS_TOKEN", "tok123")
    monkeypatch.setenv("INSTAGRAM_ACCOUNT_ID", "acc456")

    # Pre-insert a post row so foreign-key reference exists
    db.execute(
        "INSERT INTO posts (id, topic_id, format, hook, content_json, status, created_at) "
        "VALUES (1, NULL, 'carousel', NULL, NULL, 'draft', '2024-01-01T00:00:00')"
    )
    db.commit()

    # Mock 1: create item container for the single image
    httpx_mock.add_response(json={"id": "item1"})
    # Mock 2: create carousel container
    httpx_mock.add_response(json={"id": "carousel1"})
    # Mock 3: publish
    httpx_mock.add_response(json={"id": "pub1"})

    poster = InstagramPoster()
    result = poster.post_carousel(
        post_id=1,
        image_urls=["http://example.com/img.jpg"],
        caption="test",
        conn=db,
    )
    assert result == "pub1"


def test_instagram_post_carousel_updates_db(httpx_mock, db, monkeypatch):
    monkeypatch.setenv("INSTAGRAM_ACCESS_TOKEN", "tok123")
    monkeypatch.setenv("INSTAGRAM_ACCOUNT_ID", "acc456")

    db.execute(
        "INSERT INTO posts (id, topic_id, format, hook, content_json, status, created_at) "
        "VALUES (1, NULL, 'carousel', NULL, NULL, 'draft', '2024-01-01T00:00:00')"
    )
    db.commit()

    httpx_mock.add_response(json={"id": "item1"})
    httpx_mock.add_response(json={"id": "carousel1"})
    httpx_mock.add_response(json={"id": "pub1"})

    poster = InstagramPoster()
    poster.post_carousel(
        post_id=1,
        image_urls=["http://example.com/img.jpg"],
        caption="test",
        conn=db,
    )

    row = db.execute("SELECT status, published_at FROM posts WHERE id=1").fetchone()
    assert row["status"] == "published"
    assert row["published_at"] is not None

    metrics = db.execute(
        "SELECT * FROM platform_metrics WHERE post_id=1 AND platform='instagram'"
    ).fetchall()
    assert len(metrics) == 1


# ---------------------------------------------------------------------------
# YouTubePoster tests
# ---------------------------------------------------------------------------

def test_youtube_raises_without_key(monkeypatch):
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    with pytest.raises(ValueError):
        YouTubePoster()


def test_youtube_post_community_success(httpx_mock, monkeypatch):
    monkeypatch.setenv("YOUTUBE_API_KEY", "ytkey789")

    httpx_mock.add_response(json={"id": "yt123"})

    poster = YouTubePoster()
    result = poster.post_community(title="T", summary="S")
    assert result == "yt123"
