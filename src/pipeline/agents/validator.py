import re
from pipeline.agents.ollama import OllamaClient
from pipeline.models import TopicCandidate, RepoInfo

_VERIFY_SYSTEM = """You are a fact-checking agent for a developer content channel.
Given a topic candidate, assess whether it is verifiable and worth publishing.

Respond in exactly this format:
VERDICT: APPROVED or REJECTED
NOTES: <one sentence reason>"""

_REPO_SYSTEM = """You are assessing a GitHub repository for developer content value.
Consider: activity (recent commits/releases), documentation quality, ease of install, community size.

Respond in exactly this format:
SCORE: <number 0-10>
NOTES: <one sentence reason>"""


class ValidationAgent:
    def __init__(self, llm: OllamaClient | None = None) -> None:
        self.llm = llm or OllamaClient()

    def verify_claim(self, candidate: TopicCandidate) -> TopicCandidate:
        prompt = (
            f"Title: {candidate.title}\n"
            f"Summary: {candidate.summary}\n"
            f"Source URL: {candidate.source.url}\n"
            f"Source type: {candidate.source.source_type}\n\n"
            "Is this verifiable and worth publishing to developers?"
        )
        response = self.llm.chat(prompt, system=_VERIFY_SYSTEM)
        verdict_match = re.search(r"VERDICT:\s*(APPROVED|REJECTED)", response, re.IGNORECASE)
        if verdict_match:
            verdict = verdict_match.group(1).upper()
            candidate = candidate.model_copy(
                update={"status": "approved" if verdict == "APPROVED" else "rejected"}
            )
        return candidate

    def score_repo(self, repo: RepoInfo) -> RepoInfo:
        prompt = (
            f"Repository: {repo.full_name}\n"
            f"Stars: {repo.stars}\n"
            f"Language: {repo.language}\n"
            f"Description: {repo.description}\n"
            f"License: {repo.license}\n\n"
            "Score this repository for developer content value (0-10)."
        )
        response = self.llm.chat(prompt, system=_REPO_SYSTEM)
        score_match = re.search(r"SCORE:\s*(\d+(?:\.\d+)?)", response)
        if score_match:
            repo = repo.model_copy(update={"score": float(score_match.group(1))})
        return repo
