import sqlite3
from pipeline.db import get_db, init_db

def test_init_creates_tables():
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    assert {"sources", "topics", "tools", "repositories", "research",
            "claims", "posts", "videos", "scripts", "hooks",
            "platform_metrics", "affiliate_links", "products", "conversions"} <= tables

def test_get_db_returns_connection(tmp_path):
    import os
    os.environ["DB_PATH"] = str(tmp_path / "test.db")
    conn = get_db()
    assert isinstance(conn, sqlite3.Connection)
    conn.close()
