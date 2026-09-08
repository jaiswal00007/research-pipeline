import os
import sqlite3

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    url         TEXT NOT NULL UNIQUE,
    source_type TEXT NOT NULL,   -- github | hackernews | reddit | rss
    fetched_at  TEXT NOT NULL,
    raw_json    TEXT
);

CREATE TABLE IF NOT EXISTS topics (
    id              INTEGER PRIMARY KEY,
    title           TEXT NOT NULL,
    summary         TEXT,
    source_id       INTEGER REFERENCES sources(id),
    score_total     REAL,
    score_usefulness    REAL,
    score_novelty       REAL,
    score_dev_value     REAL,
    score_search_demand REAL,
    score_monetization  REAL,
    score_ease_demo     REAL,
    status          TEXT NOT NULL DEFAULT 'pending',  -- pending | approved | rejected
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tools (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    url         TEXT,
    description TEXT,
    topic_id    INTEGER REFERENCES topics(id),
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS repositories (
    id              INTEGER PRIMARY KEY,
    full_name       TEXT NOT NULL UNIQUE,
    url             TEXT NOT NULL,
    description     TEXT,
    stars           INTEGER,
    language        TEXT,
    license         TEXT,
    readme_summary  TEXT,
    install_works   INTEGER,  -- 0 | 1 | NULL (not tested)
    score           REAL,
    fetched_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS research (
    id          INTEGER PRIMARY KEY,
    topic_id    INTEGER REFERENCES topics(id),
    summary     TEXT NOT NULL,
    sources     TEXT,  -- JSON array of URLs
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS claims (
    id              INTEGER PRIMARY KEY,
    topic_id        INTEGER REFERENCES topics(id),
    claim_text      TEXT NOT NULL,
    source_url      TEXT,
    is_verified     INTEGER,  -- 0 | 1 | NULL
    verified_at     TEXT,
    verification_notes TEXT
);

CREATE TABLE IF NOT EXISTS posts (
    id              INTEGER PRIMARY KEY,
    topic_id        INTEGER REFERENCES topics(id),
    format          TEXT NOT NULL,  -- carousel | reel
    hook            TEXT,
    content_json    TEXT,
    status          TEXT NOT NULL DEFAULT 'draft',
    published_at    TEXT,
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scripts (
    id          INTEGER PRIMARY KEY,
    topic_id    INTEGER REFERENCES topics(id),
    content     TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS videos (
    id          INTEGER PRIMARY KEY,
    topic_id    INTEGER REFERENCES topics(id),
    format      TEXT NOT NULL,  -- long | short
    title       TEXT,
    script_id   INTEGER REFERENCES scripts(id),
    status      TEXT NOT NULL DEFAULT 'draft',
    published_at TEXT,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS hooks (
    id          INTEGER PRIMARY KEY,
    text        TEXT NOT NULL,
    format      TEXT,
    topic_id    INTEGER REFERENCES topics(id),
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS platform_metrics (
    id              INTEGER PRIMARY KEY,
    post_id         INTEGER REFERENCES posts(id),
    video_id        INTEGER REFERENCES videos(id),
    platform        TEXT NOT NULL,  -- instagram | youtube
    impressions     INTEGER,
    views           INTEGER,
    likes           INTEGER,
    comments        INTEGER,
    shares          INTEGER,
    saves           INTEGER,
    profile_visits  INTEGER,
    link_clicks     INTEGER,
    email_signups   INTEGER,
    revenue         REAL,
    recorded_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS affiliate_links (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    url         TEXT NOT NULL,
    commission  TEXT,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    price       REAL,
    url         TEXT,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS conversions (
    id              INTEGER PRIMARY KEY,
    affiliate_id    INTEGER REFERENCES affiliate_links(id),
    product_id      INTEGER REFERENCES products(id),
    post_id         INTEGER REFERENCES posts(id),
    amount          REAL,
    converted_at    TEXT NOT NULL
);
"""


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)
    conn.commit()


def get_db() -> sqlite3.Connection:
    path = os.environ.get("DB_PATH", "pipeline.db")
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return conn
