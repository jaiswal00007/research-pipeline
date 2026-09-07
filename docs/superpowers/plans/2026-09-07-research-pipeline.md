# Research Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the core AI research pipeline that discovers AI tools/repos from GitHub, Hacker News, and Reddit; verifies claims; scores topics; and stores everything in a local database — feeding all downstream content generation.

**Architecture:** A Python CLI application with three sequential stages: (1) source discovery that polls GitHub/HN/Reddit APIs and RSS feeds, (2) a validation agent that uses Ollama+Qwen to verify claims and score GitHub repos, (3) a topic scorer that ranks candidates on 6 dimensions and writes approved topics to a SQLite database. Each stage is a standalone module callable independently or chained via a pipeline runner.

**Tech Stack:** Python 3.11+, SQLite (initial), Ollama + Qwen3 (local LLM), httpx (async HTTP), pydantic (data models), pytest (tests), uv (package manager)

## Global Constraints

- Python 3.11+ only — use `match` statements and `tomllib` where appropriate
- SQLite for now — schema must be forward-compatible with PostgreSQL (no SQLite-isms in SQL)
- Ollama must be running locally at `http://localhost:11434` — all LLM calls go through it
- All secrets (API keys, tokens) via environment variables, never hardcoded
- No async frameworks (no FastAPI, no Celery) — plain sync Python with `httpx` for HTTP
- YAGNI: no Instagram/YouTube publishing code in this plan — that's a separate phase

---

## File Structure

```
socialmedia/
├── pyproject.toml               # project metadata, deps, scripts
├── .env.example                 # documented env vars, no secrets
├── README.md                    # setup + usage instructions
├── src/
│   └── pipeline/
│       ├── __init__.py
│       ├── db.py                # SQLite connection + schema init
│       ├── models.py            # Pydantic data models (Source, Topic, Repo, Claim)
│       ├── sources/
│       │   ├── __init__.py
│       │   ├── github.py        # GitHub trending + search API
│       │   ├── hackernews.py    # HN Algolia API (stories about AI)
│       │   └── reddit.py        # Reddit JSON API (r/MachineLearning, r/LocalLLaMA, etc.)
│       ├── agents/
│       │   ├── __init__.py
│       │   ├── ollama.py        # Ollama HTTP client wrapper
│       │   ├── researcher.py    # summarises a raw source into a structured finding
│       │   └── validator.py     # verifies claims; scores GitHub repos
│       ├── scorer.py            # topic scoring (6 dimensions → total)
│       └── runner.py            # CLI entry point: runs full pipeline
└── tests/
    ├── conftest.py              # shared fixtures (in-memory DB, mock Ollama)
    ├── test_db.py
    ├── test_models.py
    ├── test_sources_github.py
    ├── test_sources_hn.py
    ├── test_sources_reddit.py
    ├── test_ollama.py
    ├── test_researcher.py
    ├── test_validator.py
    ├── test_scorer.py
    └── test_runner.py
```

---

## Task 1: Project Scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `src/pipeline/__init__.py`
- Create: `src/pipeline/sources/__init__.py`
- Create: `src/pipeline/agents/__init__.py`

- [ ] **Step 1: Install uv if not present**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Expected: `uv` available at `~/.cargo/bin/uv` or `/usr/local/bin/uv`

- [ ] **Step 2: Initialise the project**

```bash
cd /Users/I750841/work/anshu2.0/socialmedia
uv init --python 3.11
uv add httpx pydantic python-dotenv
uv add --dev pytest pytest-httpx ruff
```

- [ ] **Step 3: Replace the generated pyproject.toml with this**

```toml
[project]
name = "pipeline"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "httpx>=0.27",
    "pydantic>=2.7",
    "python-dotenv>=1.0",
]

[project.scripts]
pipeline = "pipeline.runner:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/pipeline"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]

[tool.ruff]
line-length = 100

[dependency-groups]
dev = [
    "pytest>=8",
    "pytest-httpx>=0.30",
    "ruff>=0.4",
]
```

- [ ] **Step 4: Create .env.example**

```bash
# GitHub personal access token (optional — raises rate limit from 60 to 5000 req/hr)
GITHUB_TOKEN=

# Reddit app credentials (optional — anonymous API works but is rate-limited)
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REDDIT_USER_AGENT=pipeline/0.1

# Ollama base URL (default: local)
OLLAMA_BASE_URL=http://localhost:11434

# Ollama model to use
OLLAMA_MODEL=qwen3:8b
```

- [ ] **Step 5: Create package __init__ files**

```bash
mkdir -p src/pipeline/sources src/pipeline/agents tests
touch src/pipeline/__init__.py src/pipeline/sources/__init__.py src/pipeline/agents/__init__.py
```

- [ ] **Step 6: Verify the environment runs**

```bash
uv run python -c "import pipeline; print('ok')"
```

Expected: `ok`

- [ ] **Step 7: Commit**

```bash
git init
git add pyproject.toml .env.example src/ tests/
git commit -m "chore: initialise research pipeline project"
```

---

## Task 2: Database Schema

**Files:**
- Create: `src/pipeline/db.py`
- Create: `tests/test_db.py`

**Interfaces:**
- Produces: `get_db() -> sqlite3.Connection`, `init_db(conn)`, used by all later tasks

- [ ] **Step 1: Write the failing test**

```python
# tests/test_db.py
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
```

- [ ] **Step 2: Run to verify it fails**

```bash
uv run pytest tests/test_db.py -v
```

Expected: `ImportError: cannot import name 'get_db' from 'pipeline.db'`

- [ ] **Step 3: Implement db.py**

```python
# src/pipeline/db.py
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

CREATE TABLE IF NOT EXISTS scripts (
    id          INTEGER PRIMARY KEY,
    topic_id    INTEGER REFERENCES topics(id),
    content     TEXT NOT NULL,
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
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_db.py -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/pipeline/db.py tests/test_db.py
git commit -m "feat: database schema with all 14 tables"
```

---

## Task 3: Pydantic Data Models

**Files:**
- Create: `src/pipeline/models.py`
- Create: `tests/test_models.py`

**Interfaces:**
- Produces: `RawSource`, `TopicCandidate`, `RepoInfo`, `Claim`, `TopicScore` — used by all agents and sources

- [ ] **Step 1: Write the failing test**

```python
# tests/test_models.py
from pipeline.models import RawSource, TopicCandidate, RepoInfo, TopicScore

def test_raw_source_fields():
    s = RawSource(
        url="https://github.com/foo/bar",
        title="foo",
        source_type="github",
        fetched_at="2026-09-07T00:00:00",
        raw={},
    )
    assert s.source_type == "github"

def test_topic_score_total():
    ts = TopicScore(
        usefulness=8, novelty=7, dev_value=9,
        search_demand=6, monetization=5, ease_demo=10
    )
    assert ts.total == 45

def test_repo_info_optional_fields():
    r = RepoInfo(full_name="foo/bar", url="https://github.com/foo/bar", stars=100)
    assert r.license is None
    assert r.install_works is None
```

- [ ] **Step 2: Run to verify it fails**

```bash
uv run pytest tests/test_models.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement models.py**

```python
# src/pipeline/models.py
from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, computed_field


SourceType = Literal["github", "hackernews", "reddit", "rss"]


class RawSource(BaseModel):
    url: str
    title: str
    source_type: SourceType
    fetched_at: str  # ISO8601
    raw: dict[str, Any] = {}


class TopicScore(BaseModel):
    usefulness: float
    novelty: float
    dev_value: float
    search_demand: float
    monetization: float
    ease_demo: float

    @computed_field
    @property
    def total(self) -> float:
        return (
            self.usefulness + self.novelty + self.dev_value
            + self.search_demand + self.monetization + self.ease_demo
        )


class TopicCandidate(BaseModel):
    title: str
    summary: str
    source: RawSource
    score: TopicScore | None = None
    status: Literal["pending", "approved", "rejected"] = "pending"


class Claim(BaseModel):
    text: str
    source_url: str | None = None
    is_verified: bool | None = None
    verification_notes: str | None = None


class RepoInfo(BaseModel):
    full_name: str
    url: str
    stars: int = 0
    language: str | None = None
    description: str | None = None
    license: str | None = None
    readme_summary: str | None = None
    install_works: bool | None = None
    score: float | None = None
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_models.py -v
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/pipeline/models.py tests/test_models.py
git commit -m "feat: pydantic data models for pipeline"
```

---

## Task 4: Ollama Client

**Files:**
- Create: `src/pipeline/agents/ollama.py`
- Create: `tests/test_ollama.py`

**Interfaces:**
- Produces: `OllamaClient.chat(prompt: str, system: str | None) -> str` — used by researcher and validator

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ollama.py
import pytest
import httpx
from pytest_httpx import HTTPXMock
from pipeline.agents.ollama import OllamaClient

def test_chat_returns_text(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="http://localhost:11434/api/chat",
        json={"message": {"content": "Hello from Qwen"}},
    )
    client = OllamaClient(base_url="http://localhost:11434", model="qwen3:8b")
    result = client.chat("Say hello")
    assert result == "Hello from Qwen"

def test_chat_includes_system_prompt(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="http://localhost:11434/api/chat",
        json={"message": {"content": "Done"}},
    )
    client = OllamaClient(base_url="http://localhost:11434", model="qwen3:8b")
    client.chat("Do something", system="You are a researcher")
    request = httpx_mock.get_requests()[0]
    import json
    body = json.loads(request.content)
    assert body["messages"][0]["role"] == "system"
    assert body["messages"][0]["content"] == "You are a researcher"
```

- [ ] **Step 2: Run to verify it fails**

```bash
uv run pytest tests/test_ollama.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement ollama.py**

```python
# src/pipeline/agents/ollama.py
import os
import httpx


class OllamaClient:
    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self.base_url = (base_url or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        self.model = model or os.environ.get("OLLAMA_MODEL", "qwen3:8b")

    def chat(self, prompt: str, system: str | None = None) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = httpx.post(
            f"{self.base_url}/api/chat",
            json={"model": self.model, "messages": messages, "stream": False},
            timeout=120,
        )
        response.raise_for_status()
        return response.json()["message"]["content"]
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_ollama.py -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/pipeline/agents/ollama.py tests/test_ollama.py
git commit -m "feat: Ollama HTTP client wrapper"
```

---

## Task 5: GitHub Source Discovery

**Files:**
- Create: `src/pipeline/sources/github.py`
- Create: `tests/test_sources_github.py`

**Interfaces:**
- Produces: `fetch_github_trending(token: str | None) -> list[RawSource]`, `search_github_ai(query: str, token: str | None) -> list[RawSource]`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_sources_github.py
import pytest
from pytest_httpx import HTTPXMock
from pipeline.sources.github import fetch_github_trending, search_github_ai

SAMPLE_SEARCH_RESPONSE = {
    "items": [
        {
            "full_name": "owner/cool-ai-tool",
            "html_url": "https://github.com/owner/cool-ai-tool",
            "description": "A cool AI tool",
            "stargazers_count": 1200,
            "language": "Python",
            "license": {"spdx_id": "MIT"},
        }
    ]
}

def test_search_github_ai_returns_sources(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url__regex=r"https://api\.github\.com/search/repositories.*",
        json=SAMPLE_SEARCH_RESPONSE,
    )
    results = search_github_ai("AI coding agent", token=None)
    assert len(results) == 1
    assert results[0].source_type == "github"
    assert results[0].url == "https://github.com/owner/cool-ai-tool"
    assert results[0].title == "owner/cool-ai-tool"

def test_search_github_ai_sets_fetched_at(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url__regex=r"https://api\.github\.com/search/repositories.*",
        json=SAMPLE_SEARCH_RESPONSE,
    )
    results = search_github_ai("AI", token=None)
    assert results[0].fetched_at  # non-empty ISO string
```

- [ ] **Step 2: Run to verify it fails**

```bash
uv run pytest tests/test_sources_github.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement github.py**

```python
# src/pipeline/sources/github.py
import os
from datetime import datetime, timezone
import httpx
from pipeline.models import RawSource

_BASE = "https://api.github.com"
_AI_QUERIES = [
    "AI coding agent",
    "LLM developer tool",
    "local AI assistant",
    "open source AI workflow",
]


def _headers(token: str | None) -> dict[str, str]:
    h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    t = token or os.environ.get("GITHUB_TOKEN")
    if t:
        h["Authorization"] = f"Bearer {t}"
    return h


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def search_github_ai(query: str, token: str | None = None) -> list[RawSource]:
    params = {"q": f"{query} language:Python stars:>50", "sort": "stars", "per_page": 10}
    resp = httpx.get(f"{_BASE}/search/repositories", params=params, headers=_headers(token), timeout=15)
    resp.raise_for_status()
    items = resp.json().get("items", [])
    return [
        RawSource(
            url=item["html_url"],
            title=item["full_name"],
            source_type="github",
            fetched_at=_now(),
            raw=item,
        )
        for item in items
    ]


def fetch_github_trending(token: str | None = None) -> list[RawSource]:
    all_results: list[RawSource] = []
    for q in _AI_QUERIES:
        all_results.extend(search_github_ai(q, token=token))
    seen: set[str] = set()
    unique = []
    for s in all_results:
        if s.url not in seen:
            seen.add(s.url)
            unique.append(s)
    return unique
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_sources_github.py -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/pipeline/sources/github.py tests/test_sources_github.py
git commit -m "feat: GitHub source discovery"
```

---

## Task 6: Hacker News Source Discovery

**Files:**
- Create: `src/pipeline/sources/hackernews.py`
- Create: `tests/test_sources_hn.py`

**Interfaces:**
- Produces: `fetch_hn_ai_stories(min_points: int) -> list[RawSource]`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_sources_hn.py
from pytest_httpx import HTTPXMock
from pipeline.sources.hackernews import fetch_hn_ai_stories

SAMPLE_HN = {
    "hits": [
        {
            "objectID": "12345",
            "title": "Show HN: Open-source AI coding assistant",
            "url": "https://example.com/ai-tool",
            "points": 300,
            "author": "dev123",
        }
    ]
}

def test_fetch_hn_stories_returns_sources(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url__regex=r"https://hn\.algolia\.com/api/v1/search.*",
        json=SAMPLE_HN,
    )
    results = fetch_hn_ai_stories(min_points=100)
    assert len(results) == 1
    assert results[0].source_type == "hackernews"
    assert results[0].title == "Show HN: Open-source AI coding assistant"

def test_fetch_hn_filters_low_points(httpx_mock: HTTPXMock):
    low_points = {"hits": [{"objectID": "1", "title": "Meh", "url": "https://x.com", "points": 5, "author": "x"}]}
    httpx_mock.add_response(
        url__regex=r"https://hn\.algolia\.com/api/v1/search.*",
        json=low_points,
    )
    results = fetch_hn_ai_stories(min_points=100)
    assert results == []
```

- [ ] **Step 2: Run to verify it fails**

```bash
uv run pytest tests/test_sources_hn.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement hackernews.py**

```python
# src/pipeline/sources/hackernews.py
from datetime import datetime, timezone
import httpx
from pipeline.models import RawSource

_ALGOLIA = "https://hn.algolia.com/api/v1/search"
_AI_TAGS = ["AI", "LLM", "machine learning", "open source AI", "coding agent"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def fetch_hn_ai_stories(min_points: int = 100) -> list[RawSource]:
    query = " OR ".join(_AI_TAGS)
    params = {
        "query": query,
        "tags": "story",
        "hitsPerPage": 30,
        "numericFilters": f"points>{min_points}",
    }
    resp = httpx.get(_ALGOLIA, params=params, timeout=15)
    resp.raise_for_status()
    hits = resp.json().get("hits", [])
    results = []
    for hit in hits:
        if hit.get("points", 0) <= min_points:
            continue
        url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit['objectID']}"
        results.append(RawSource(
            url=url,
            title=hit.get("title", ""),
            source_type="hackernews",
            fetched_at=_now(),
            raw=hit,
        ))
    return results
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_sources_hn.py -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/pipeline/sources/hackernews.py tests/test_sources_hn.py
git commit -m "feat: Hacker News source discovery"
```

---

## Task 7: Reddit Source Discovery

**Files:**
- Create: `src/pipeline/sources/reddit.py`
- Create: `tests/test_sources_reddit.py`

**Interfaces:**
- Produces: `fetch_reddit_ai_posts(subreddits: list[str], limit: int) -> list[RawSource]`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_sources_reddit.py
from pytest_httpx import HTTPXMock
from pipeline.sources.reddit import fetch_reddit_ai_posts

SAMPLE_REDDIT = {
    "data": {
        "children": [
            {"data": {
                "id": "abc123",
                "title": "New open source AI coding tool",
                "url": "https://github.com/foo/bar",
                "permalink": "/r/MachineLearning/comments/abc123/",
                "score": 500,
                "selftext": "Check out this tool",
            }}
        ]
    }
}

def test_fetch_reddit_posts(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url__regex=r"https://www\.reddit\.com/r/.*",
        json=SAMPLE_REDDIT,
    )
    results = fetch_reddit_ai_posts(["MachineLearning"], limit=5)
    assert len(results) == 1
    assert results[0].source_type == "reddit"
    assert results[0].title == "New open source AI coding tool"

def test_fetch_reddit_multiple_subreddits(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url__regex=r"https://www\.reddit\.com/r/.*",
        json=SAMPLE_REDDIT,
    )
    results = fetch_reddit_ai_posts(["MachineLearning", "LocalLLaMA"], limit=5)
    assert len(results) == 2  # one per subreddit (dedup by url may reduce)
```

- [ ] **Step 2: Run to verify it fails**

```bash
uv run pytest tests/test_sources_reddit.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement reddit.py**

```python
# src/pipeline/sources/reddit.py
import os
from datetime import datetime, timezone
import httpx
from pipeline.models import RawSource

_DEFAULT_SUBS = ["MachineLearning", "LocalLLaMA", "artificial", "singularity", "Programming"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
                fetched_at=_now(),
                raw=post,
            ))
    return results
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_sources_reddit.py -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/pipeline/sources/reddit.py tests/test_sources_reddit.py
git commit -m "feat: Reddit source discovery"
```

---

## Task 8: Research Agent

**Files:**
- Create: `src/pipeline/agents/researcher.py`
- Create: `tests/test_researcher.py`

**Interfaces:**
- Consumes: `OllamaClient.chat(prompt, system) -> str` (from Task 4), `RawSource` (from Task 3)
- Produces: `ResearchAgent.summarise(source: RawSource) -> TopicCandidate`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_researcher.py
from unittest.mock import MagicMock
from pipeline.agents.researcher import ResearchAgent
from pipeline.models import RawSource, TopicCandidate

def _make_source():
    return RawSource(
        url="https://github.com/foo/bar",
        title="foo/bar",
        source_type="github",
        fetched_at="2026-09-07T00:00:00",
        raw={"description": "An AI coding agent", "stargazers_count": 1000},
    )

def test_summarise_returns_topic_candidate():
    mock_llm = MagicMock()
    mock_llm.chat.return_value = (
        "TITLE: AI Coding Agent foo/bar\n"
        "SUMMARY: An open-source AI coding agent with 1000 stars on GitHub."
    )
    agent = ResearchAgent(llm=mock_llm)
    result = agent.summarise(_make_source())
    assert isinstance(result, TopicCandidate)
    assert "foo/bar" in result.title or "AI" in result.title
    assert len(result.summary) > 10

def test_summarise_calls_llm_with_source_info():
    mock_llm = MagicMock()
    mock_llm.chat.return_value = "TITLE: Test\nSUMMARY: A test tool."
    agent = ResearchAgent(llm=mock_llm)
    agent.summarise(_make_source())
    call_prompt = mock_llm.chat.call_args[0][0]
    assert "foo/bar" in call_prompt or "github" in call_prompt.lower()
```

- [ ] **Step 2: Run to verify it fails**

```bash
uv run pytest tests/test_researcher.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement researcher.py**

```python
# src/pipeline/agents/researcher.py
import re
from datetime import datetime, timezone
from pipeline.agents.ollama import OllamaClient
from pipeline.models import RawSource, TopicCandidate

_SYSTEM = """You are a research assistant for an AI developer content channel.
Given information about a source (GitHub repo, HN story, Reddit post), extract
the key insight for a developer audience.

Respond in exactly this format:
TITLE: <concise title for potential content>
SUMMARY: <2-3 sentences explaining what it is and why developers should care>"""


class ResearchAgent:
    def __init__(self, llm: OllamaClient | None = None) -> None:
        self.llm = llm or OllamaClient()

    def summarise(self, source: RawSource) -> TopicCandidate:
        prompt = (
            f"Source type: {source.source_type}\n"
            f"Title: {source.title}\n"
            f"URL: {source.url}\n"
            f"Details: {_format_raw(source.raw)}\n\n"
            "Extract the content opportunity."
        )
        response = self.llm.chat(prompt, system=_SYSTEM)
        title, summary = _parse_response(response, fallback_title=source.title)
        return TopicCandidate(
            title=title,
            summary=summary,
            source=source,
        )


def _format_raw(raw: dict) -> str:
    interesting = {k: v for k, v in raw.items()
                   if k in ("description", "stargazers_count", "language",
                            "points", "score", "selftext", "body")}
    return str(interesting)[:500]


def _parse_response(text: str, fallback_title: str) -> tuple[str, str]:
    title_match = re.search(r"TITLE:\s*(.+)", text)
    summary_match = re.search(r"SUMMARY:\s*(.+)", text, re.DOTALL)
    title = title_match.group(1).strip() if title_match else fallback_title
    summary = summary_match.group(1).strip() if summary_match else text.strip()
    return title, summary
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_researcher.py -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/pipeline/agents/researcher.py tests/test_researcher.py
git commit -m "feat: research agent (LLM-powered source summariser)"
```

---

## Task 9: Validation Agent

**Files:**
- Create: `src/pipeline/agents/validator.py`
- Create: `tests/test_validator.py`

**Interfaces:**
- Consumes: `OllamaClient.chat(prompt, system) -> str` (Task 4), `TopicCandidate` (Task 3), `RepoInfo` (Task 3)
- Produces: `ValidationAgent.verify_claim(candidate: TopicCandidate) -> TopicCandidate`, `ValidationAgent.score_repo(repo: RepoInfo) -> RepoInfo`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_validator.py
from unittest.mock import MagicMock
from pipeline.agents.validator import ValidationAgent
from pipeline.models import RawSource, TopicCandidate, RepoInfo

def _make_candidate():
    source = RawSource(
        url="https://github.com/foo/bar",
        title="foo/bar",
        source_type="github",
        fetched_at="2026-09-07T00:00:00",
        raw={},
    )
    return TopicCandidate(title="Test Tool", summary="A useful AI tool.", source=source)

def test_verify_claim_approved():
    mock_llm = MagicMock()
    mock_llm.chat.return_value = "VERDICT: APPROVED\nNOTES: Source is reliable and reproducible."
    agent = ValidationAgent(llm=mock_llm)
    result = agent.verify_claim(_make_candidate())
    assert result.status == "approved"

def test_verify_claim_rejected():
    mock_llm = MagicMock()
    mock_llm.chat.return_value = "VERDICT: REJECTED\nNOTES: Cannot verify source."
    agent = ValidationAgent(llm=mock_llm)
    result = agent.verify_claim(_make_candidate())
    assert result.status == "rejected"

def test_score_repo_sets_score():
    mock_llm = MagicMock()
    mock_llm.chat.return_value = "SCORE: 7.5\nNOTES: Active repo, good docs."
    agent = ValidationAgent(llm=mock_llm)
    repo = RepoInfo(full_name="foo/bar", url="https://github.com/foo/bar", stars=500)
    result = agent.score_repo(repo)
    assert result.score == 7.5
```

- [ ] **Step 2: Run to verify it fails**

```bash
uv run pytest tests/test_validator.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement validator.py**

```python
# src/pipeline/agents/validator.py
import re
from pipeline.agents.ollama import OllamaClient
from pipeline.models import TopicCandidate, RepoInfo

_VERIFY_SYSTEM = """You are a fact-checking agent for a developer content channel.
Given a topic candidate, assess whether it is verifiable and worth publishing.

Respond in exactly this format:
VERDICT: APPROVED or REJECTED
NOTES: <one sentence reason>"""

_REPO_SYSTEM = """You are assessing a GitHub repository for developer content value.
Consider: activity (recent commits/releases), documentation quality, ease of install, community size.

Respond in exactly this format:
SCORE: <number 0-10>
NOTES: <one sentence reason>"""


class ValidationAgent:
    def __init__(self, llm: OllamaClient | None = None) -> None:
        self.llm = llm or OllamaClient()

    def verify_claim(self, candidate: TopicCandidate) -> TopicCandidate:
        prompt = (
            f"Title: {candidate.title}\n"
            f"Summary: {candidate.summary}\n"
            f"Source URL: {candidate.source.url}\n"
            f"Source type: {candidate.source.source_type}\n\n"
            "Is this verifiable and worth publishing to developers?"
        )
        response = self.llm.chat(prompt, system=_VERIFY_SYSTEM)
        verdict_match = re.search(r"VERDICT:\s*(APPROVED|REJECTED)", response, re.IGNORECASE)
        if verdict_match:
            verdict = verdict_match.group(1).upper()
            candidate = candidate.model_copy(
                update={"status": "approved" if verdict == "APPROVED" else "rejected"}
            )
        return candidate

    def score_repo(self, repo: RepoInfo) -> RepoInfo:
        prompt = (
            f"Repository: {repo.full_name}\n"
            f"Stars: {repo.stars}\n"
            f"Language: {repo.language}\n"
            f"Description: {repo.description}\n"
            f"License: {repo.license}\n\n"
            "Score this repository for developer content value (0-10)."
        )
        response = self.llm.chat(prompt, system=_REPO_SYSTEM)
        score_match = re.search(r"SCORE:\s*(\d+(?:\.\d+)?)", response)
        if score_match:
            repo = repo.model_copy(update={"score": float(score_match.group(1))})
        return repo
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_validator.py -v
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/pipeline/agents/validator.py tests/test_validator.py
git commit -m "feat: validation agent (claim verifier + repo scorer)"
```

---

## Task 10: Topic Scorer

**Files:**
- Create: `src/pipeline/scorer.py`
- Create: `tests/test_scorer.py`

**Interfaces:**
- Consumes: `OllamaClient.chat(prompt, system) -> str` (Task 4), `TopicCandidate` (Task 3)
- Produces: `TopicScorer.score(candidate: TopicCandidate) -> TopicCandidate` with `candidate.score` populated

- [ ] **Step 1: Write the failing test**

```python
# tests/test_scorer.py
from unittest.mock import MagicMock
from pipeline.scorer import TopicScorer
from pipeline.models import RawSource, TopicCandidate

def _make_candidate():
    source = RawSource(
        url="https://github.com/foo/bar",
        title="foo/bar",
        source_type="github",
        fetched_at="2026-09-07T00:00:00",
        raw={},
    )
    return TopicCandidate(title="AI Tool", summary="A useful AI tool.", source=source)

def test_scorer_populates_score():
    mock_llm = MagicMock()
    mock_llm.chat.return_value = (
        "USEFULNESS: 8\nNOVELTY: 7\nDEV_VALUE: 9\n"
        "SEARCH_DEMAND: 6\nMONETIZATION: 5\nEASE_DEMO: 8"
    )
    scorer = TopicScorer(llm=mock_llm)
    result = scorer.score(_make_candidate())
    assert result.score is not None
    assert result.score.total == 43

def test_scorer_marks_high_score_approved():
    mock_llm = MagicMock()
    mock_llm.chat.return_value = (
        "USEFULNESS: 9\nNOVELTY: 9\nDEV_VALUE: 9\n"
        "SEARCH_DEMAND: 9\nMONETIZATION: 8\nEASE_DEMO: 9"
    )
    scorer = TopicScorer(llm=mock_llm, approval_threshold=40)
    result = scorer.score(_make_candidate())
    assert result.status == "approved"

def test_scorer_marks_low_score_rejected():
    mock_llm = MagicMock()
    mock_llm.chat.return_value = (
        "USEFULNESS: 2\nNOVELTY: 2\nDEV_VALUE: 2\n"
        "SEARCH_DEMAND: 2\nMONETIZATION: 1\nEASE_DEMO: 1"
    )
    scorer = TopicScorer(llm=mock_llm, approval_threshold=40)
    result = scorer.score(_make_candidate())
    assert result.status == "rejected"
```

- [ ] **Step 2: Run to verify it fails**

```bash
uv run pytest tests/test_scorer.py -v
```

Expected: `ImportError`

- [ ] **Step 3: Implement scorer.py**

```python
# src/pipeline/scorer.py
import re
from pipeline.agents.ollama import OllamaClient
from pipeline.models import TopicCandidate, TopicScore

_SYSTEM = """You are scoring a content topic for an AI developer channel.
Score each dimension 0–10 based on how well this topic serves the audience.

Respond in exactly this format (one per line):
USEFULNESS: <0-10>
NOVELTY: <0-10>
DEV_VALUE: <0-10>
SEARCH_DEMAND: <0-10>
MONETIZATION: <0-10>
EASE_DEMO: <0-10>"""


class TopicScorer:
    def __init__(
        self,
        llm: OllamaClient | None = None,
        approval_threshold: float = 35,
    ) -> None:
        self.llm = llm or OllamaClient()
        self.approval_threshold = approval_threshold

    def score(self, candidate: TopicCandidate) -> TopicCandidate:
        prompt = (
            f"Title: {candidate.title}\n"
            f"Summary: {candidate.summary}\n"
            f"Source: {candidate.source.source_type} — {candidate.source.url}\n\n"
            "Score this topic across the 6 dimensions."
        )
        response = self.llm.chat(prompt, system=_SYSTEM)
        topic_score = _parse_scores(response)
        status = "approved" if topic_score.total >= self.approval_threshold else "rejected"
        return candidate.model_copy(update={"score": topic_score, "status": status})


def _parse_scores(text: str) -> TopicScore:
    def extract(key: str) -> float:
        m = re.search(rf"{key}:\s*(\d+(?:\.\d+)?)", text, re.IGNORECASE)
        return float(m.group(1)) if m else 5.0  # default to midpoint if missing

    return TopicScore(
        usefulness=extract("USEFULNESS"),
        novelty=extract("NOVELTY"),
        dev_value=extract("DEV_VALUE"),
        search_demand=extract("SEARCH_DEMAND"),
        monetization=extract("MONETIZATION"),
        ease_demo=extract("EASE_DEMO"),
    )
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/test_scorer.py -v
```

Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/pipeline/scorer.py tests/test_scorer.py
git commit -m "feat: topic scorer with 6-dimension LLM scoring"
```

---

## Task 11: Pipeline Runner + Persistence

**Files:**
- Create: `src/pipeline/runner.py`
- Create: `tests/conftest.py`
- Create: `tests/test_runner.py`

**Interfaces:**
- Consumes: all modules from Tasks 2–10
- Produces: `run_pipeline(db_conn, llm) -> list[TopicCandidate]` and `main()` CLI entry point

- [ ] **Step 1: Create conftest.py with shared fixtures**

```python
# tests/conftest.py
import sqlite3
import pytest
from pipeline.db import init_db

@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    yield conn
    conn.close()
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_runner.py
from unittest.mock import MagicMock, patch
from pipeline.runner import run_pipeline
from pipeline.models import RawSource, TopicCandidate, TopicScore

def _approved_candidate():
    source = RawSource(
        url="https://github.com/foo/bar",
        title="foo/bar",
        source_type="github",
        fetched_at="2026-09-07T00:00:00",
        raw={},
    )
    score = TopicScore(usefulness=9, novelty=8, dev_value=9, search_demand=7, monetization=6, ease_demo=8)
    return TopicCandidate(title="Great AI Tool", summary="Useful.", source=source, score=score, status="approved")

def test_run_pipeline_saves_approved_topics(db):
    mock_llm = MagicMock()

    with patch("pipeline.runner.fetch_github_trending", return_value=[
        RawSource(url="https://github.com/a/b", title="a/b", source_type="github",
                  fetched_at="2026-09-07T00:00:00", raw={})
    ]), patch("pipeline.runner.fetch_hn_ai_stories", return_value=[]), \
       patch("pipeline.runner.fetch_reddit_ai_posts", return_value=[]), \
       patch("pipeline.runner.ResearchAgent") as MockResearcher, \
       patch("pipeline.runner.ValidationAgent") as MockValidator, \
       patch("pipeline.runner.TopicScorer") as MockScorer:

        MockResearcher.return_value.summarise.return_value = _approved_candidate()
        MockValidator.return_value.verify_claim.return_value = _approved_candidate()
        MockScorer.return_value.score.return_value = _approved_candidate()

        results = run_pipeline(db_conn=db, llm=mock_llm)

    assert len(results) >= 1
    row = db.execute("SELECT * FROM topics WHERE status='approved'").fetchone()
    assert row is not None
```

- [ ] **Step 3: Run to verify it fails**

```bash
uv run pytest tests/test_runner.py -v
```

Expected: `ImportError`

- [ ] **Step 4: Implement runner.py**

```python
# src/pipeline/runner.py
import os
import sys
from datetime import datetime, timezone
import sqlite3

from dotenv import load_dotenv

from pipeline.db import get_db
from pipeline.agents.ollama import OllamaClient
from pipeline.agents.researcher import ResearchAgent
from pipeline.agents.validator import ValidationAgent
from pipeline.models import RawSource, TopicCandidate
from pipeline.scorer import TopicScorer
from pipeline.sources.github import fetch_github_trending
from pipeline.sources.hackernews import fetch_hn_ai_stories
from pipeline.sources.reddit import fetch_reddit_ai_posts


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _save_source(conn: sqlite3.Connection, source: RawSource) -> int:
    import json
    cur = conn.execute(
        "INSERT OR IGNORE INTO sources (name, url, source_type, fetched_at, raw_json) VALUES (?,?,?,?,?)",
        (source.title, source.url, source.source_type, source.fetched_at, json.dumps(source.raw)),
    )
    conn.commit()
    row = conn.execute("SELECT id FROM sources WHERE url=?", (source.url,)).fetchone()
    return row["id"]


def _save_topic(conn: sqlite3.Connection, candidate: TopicCandidate, source_id: int) -> None:
    s = candidate.score
    conn.execute(
        """INSERT INTO topics
           (title, summary, source_id, score_total, score_usefulness, score_novelty,
            score_dev_value, score_search_demand, score_monetization, score_ease_demo,
            status, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            candidate.title, candidate.summary, source_id,
            s.total if s else None,
            s.usefulness if s else None, s.novelty if s else None,
            s.dev_value if s else None, s.search_demand if s else None,
            s.monetization if s else None, s.ease_demo if s else None,
            candidate.status, _now(),
        ),
    )
    conn.commit()


def run_pipeline(
    db_conn: sqlite3.Connection | None = None,
    llm: OllamaClient | None = None,
) -> list[TopicCandidate]:
    conn = db_conn or get_db()
    llm = llm or OllamaClient()

    researcher = ResearchAgent(llm=llm)
    validator = ValidationAgent(llm=llm)
    scorer = TopicScorer(llm=llm)

    print("Fetching sources...")
    sources: list[RawSource] = []
    sources.extend(fetch_github_trending())
    sources.extend(fetch_hn_ai_stories())
    sources.extend(fetch_reddit_ai_posts())
    print(f"  Found {len(sources)} raw sources")

    approved: list[TopicCandidate] = []

    for source in sources:
        print(f"  Processing: {source.title[:60]}")
        try:
            candidate = researcher.summarise(source)
            candidate = validator.verify_claim(candidate)
            if candidate.status == "rejected":
                continue
            candidate = scorer.score(candidate)
            source_id = _save_source(conn, source)
            _save_topic(conn, candidate, source_id)
            if candidate.status == "approved":
                approved.append(candidate)
        except Exception as exc:
            print(f"  Warning: skipped {source.url}: {exc}", file=sys.stderr)
            continue

    print(f"Pipeline complete. {len(approved)} approved topics saved.")
    return approved


def main() -> None:
    load_dotenv()
    approved = run_pipeline()
    for i, topic in enumerate(approved, 1):
        score_str = f"({topic.score.total:.0f}/60)" if topic.score else ""
        print(f"{i}. {topic.title} {score_str}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run tests**

```bash
uv run pytest tests/test_runner.py -v
```

Expected: 1 passed

- [ ] **Step 6: Run full test suite**

```bash
uv run pytest -v
```

Expected: all tests pass

- [ ] **Step 7: Commit**

```bash
git add src/pipeline/runner.py tests/conftest.py tests/test_runner.py
git commit -m "feat: pipeline runner with persistence and CLI entry point"
```

---

## Task 12: Install Ollama + Qwen and Smoke Test

**Files:** none (setup only)

- [ ] **Step 1: Install Ollama**

Visit https://ollama.com/download and install for macOS, or:
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

- [ ] **Step 2: Pull the Qwen model**

```bash
ollama pull qwen3:8b
```

Expected: model downloads (~5GB). Verify: `ollama list` shows `qwen3:8b`

- [ ] **Step 3: Start Ollama server**

```bash
ollama serve &
```

Or just run the Ollama app if you installed the macOS app — it runs the server in the background.

- [ ] **Step 4: Copy .env.example and add GitHub token (optional but recommended)**

```bash
cp .env.example .env
# Edit .env and add GITHUB_TOKEN if you have one (raises API rate limit)
```

- [ ] **Step 5: Run a live smoke test of the full pipeline**

```bash
uv run pipeline
```

Expected: output like:
```
Fetching sources...
  Found 42 raw sources
  Processing: owner/some-ai-tool
  Processing: Show HN: AI coding agent
  ...
Pipeline complete. 8 approved topics saved.
1. AI Coding Agent foo/bar (47/60)
2. ...
```

- [ ] **Step 6: Verify topics were saved to the database**

```bash
uv run python -c "
from pipeline.db import get_db
conn = get_db()
rows = conn.execute('SELECT title, score_total, status FROM topics ORDER BY score_total DESC').fetchall()
for r in rows: print(f'{r[\"status\"]:10} {r[\"score_total\"] or 0:5.1f}  {r[\"title\"]}')
"
```

Expected: list of topics with scores and statuses

- [ ] **Step 7: Commit**

```bash
git add .env.example
git commit -m "docs: update .env.example with Ollama model config"
```

---

## Self-Review

**Spec coverage check:**

| Requirement | Covered by |
|---|---|
| Source discovery: GitHub | Task 5 |
| Source discovery: HN | Task 6 |
| Source discovery: Reddit | Task 7 |
| Research agent (summarise) | Task 8 |
| Validation agent (verify claims) | Task 9 |
| Topic scoring (6 dimensions) | Task 10 |
| Knowledge base / database | Task 2 |
| All 14 database tables | Task 2 |
| Analytics fields per post | Task 2 (`platform_metrics`) |
| Ollama + Qwen local AI | Tasks 4, 12 |
| Python backend | All tasks |
| SQLite initially | Task 2 |
| CLI entry point | Task 11 |
| Pydantic models | Task 3 |

**Not in scope (future plans):** n8n orchestration, Instagram publishing, YouTube publishing, content generation, visual generation, newsletter, website, analytics feedback loop.

**Placeholder scan:** None found — all steps have complete code.

**Type consistency:** `TopicCandidate`, `RawSource`, `RepoInfo`, `TopicScore`, `OllamaClient` used consistently across all tasks matching Task 3/4 definitions.
