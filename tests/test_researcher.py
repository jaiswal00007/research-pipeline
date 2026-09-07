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
