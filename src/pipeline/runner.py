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
