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
