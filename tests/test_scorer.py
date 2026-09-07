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
