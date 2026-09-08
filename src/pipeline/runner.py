# src/pipeline/runner.py
import json
import sys
import sqlite3

from dotenv import load_dotenv

from pipeline.db import get_db
from pipeline.agents.ollama import OllamaClient
from pipeline.agents.researcher import ResearchAgent
from pipeline.agents.validator import ValidationAgent
from pipeline.models import RawSource, TopicCandidate, now_iso
from pipeline.scorer import TopicScorer
from pipeline.sources.arxiv import fetch_arxiv_papers
from pipeline.sources.brave import fetch_brave_search
from pipeline.sources.github import fetch_github_trending
from pipeline.sources.hackernews import fetch_hn_ai_stories
from pipeline.sources.producthunt import fetch_producthunt_launches
from pipeline.sources.rss import fetch_rss_feeds


def _save_source(conn: sqlite3.Connection, source: RawSource) -> int:
    cur = conn.execute(
        "INSERT OR IGNORE INTO sources (name, url, source_type, fetched_at, raw_json) VALUES (?,?,?,?,?)",
        (source.title, source.url, source.source_type, source.fetched_at, json.dumps(source.raw)),
    )
    conn.commit()
    row = conn.execute("SELECT id FROM sources WHERE url=?", (source.url,)).fetchone()
    if row is None:
        raise RuntimeError(f"source missing after insert: {source.url}")
    return row["id"]


def _save_topic(conn: sqlite3.Connection, candidate: TopicCandidate, source_id: int) -> int:
    s = candidate.score
    cur = conn.execute(
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
            candidate.status, now_iso(),
        ),
    )
    topic_id = cur.lastrowid
    if candidate.verification_notes is not None:
        conn.execute(
            """INSERT INTO claims (topic_id, claim_text, is_verified, verification_notes, verified_at)
               VALUES (?, ?, ?, ?, ?)""",
            (
                topic_id,
                candidate.title,
                1 if candidate.status == "approved" else 0,
                candidate.verification_notes,
                now_iso(),
            ),
        )
    conn.commit()
    return topic_id


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
    sources.extend(fetch_rss_feeds())
    sources.extend(fetch_brave_search())
    sources.extend(fetch_arxiv_papers())
    sources.extend(fetch_producthunt_launches())
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
            if candidate.score is None or candidate.score.total < scorer.approval_threshold:
                continue
            source_id = _save_source(conn, source)
            _save_topic(conn, candidate, source_id)
            approved.append(candidate.model_copy(update={"status": "approved"}))
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
