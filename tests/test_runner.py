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
       patch("pipeline.runner.fetch_rss_feeds", return_value=[]), \
       patch("pipeline.runner.fetch_brave_search", return_value=[]), \
       patch("pipeline.runner.fetch_arxiv_papers", return_value=[]), \
       patch("pipeline.runner.fetch_producthunt_launches", return_value=[]), \
       patch("pipeline.runner.ResearchAgent") as MockResearcher, \
       patch("pipeline.runner.ValidationAgent") as MockValidator, \
       patch("pipeline.runner.TopicScorer") as MockScorer:

        MockResearcher.return_value.summarise.return_value = _approved_candidate()
        MockValidator.return_value.verify_claim.return_value = _approved_candidate()
        MockScorer.return_value.score.return_value = _approved_candidate()
        MockScorer.return_value.approval_threshold = 35

        results = run_pipeline(db_conn=db, llm=mock_llm)

    assert len(results) >= 1
    row = db.execute("SELECT * FROM topics WHERE status='approved'").fetchone()
    assert row is not None
