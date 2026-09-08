import re
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
