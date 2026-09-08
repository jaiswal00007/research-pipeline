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
