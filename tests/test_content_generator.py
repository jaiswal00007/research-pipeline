import json
import pytest
from unittest.mock import MagicMock, patch

from pipeline.content.generator import CarouselGenerator


SAMPLE_CONTENT = {
    "slides": [
        {"slide": 1, "title": "Big Hook", "body": "This will change how you build AI apps forever."},
        {"slide": 2, "title": "The Problem", "body": "Most devs struggle with context length."},
        {"slide": 3, "title": "The Solution", "body": "Use RAG to extend context intelligently."},
        {"slide": 4, "title": "Tip 1", "body": "Chunk your documents properly."},
        {"slide": 5, "title": "Tip 2", "body": "Use embeddings from a proven model."},
        {"slide": 6, "title": "Tip 3", "body": "Cache your retrievals for speed."},
        {"slide": 7, "title": "Tip 4", "body": "Tune top-k retrieval per use case."},
        {"slide": 8, "title": "Practical Example", "body": "Build a customer support bot with RAG."},
        {"slide": 9, "title": "Who Should Use It", "body": "Any dev building LLM-powered tools."},
        {"slide": 10, "title": "CTA", "body": "Follow for daily AI dev tips."},
    ],
    "caption": "RAG is the missing piece for production LLM apps. Here's what you need to know.",
    "hashtags": ["#AI", "#developer", "#MachineLearning", "#LLM", "#RAG"],
}


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.chat.return_value = json.dumps(SAMPLE_CONTENT)
    return llm


def test_generate_returns_dict(db, mock_llm):
    gen = CarouselGenerator(llm=mock_llm)
    result = gen.generate(topic_id=1, title="RAG Explained", summary="What is RAG?", conn=db)
    assert isinstance(result, dict)
    assert "slides" in result
    assert "caption" in result
    assert "hashtags" in result


def test_generate_saves_post_to_db(db, mock_llm):
    gen = CarouselGenerator(llm=mock_llm)
    gen.generate(topic_id=1, title="RAG Explained", summary="What is RAG?", conn=db)
    rows = db.execute("SELECT * FROM posts").fetchall()
    assert len(rows) == 1
    assert rows[0]["format"] == "carousel"
    assert rows[0]["status"] == "pending_approval"


def test_generate_sets_hook_from_first_slide(db, mock_llm):
    gen = CarouselGenerator(llm=mock_llm)
    result = gen.generate(topic_id=1, title="RAG Explained", summary="What is RAG?", conn=db)
    row = db.execute("SELECT hook FROM posts").fetchone()
    assert row["hook"] == result["slides"][0]["body"]


def test_generate_strips_markdown_fences(db, mock_llm):
    mock_llm.chat.return_value = f"```json\n{json.dumps(SAMPLE_CONTENT)}\n```"
    gen = CarouselGenerator(llm=mock_llm)
    result = gen.generate(topic_id=1, title="RAG Explained", summary="What is RAG?", conn=db)
    assert isinstance(result, dict)
    assert "slides" in result
    assert len(result["slides"]) == 10


def test_generate_raises_on_invalid_json(db, mock_llm):
    mock_llm.chat.return_value = "Sorry, I cannot generate that content."
    gen = CarouselGenerator(llm=mock_llm)
    with pytest.raises(ValueError, match="LLM returned invalid JSON"):
        gen.generate(topic_id=1, title="RAG Explained", summary="What is RAG?", conn=db)
