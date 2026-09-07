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
