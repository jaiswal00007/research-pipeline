from __future__ import annotations
from typing import Any, Literal
from pydantic import BaseModel, computed_field


SourceType = Literal["github", "hackernews", "reddit", "rss"]


class RawSource(BaseModel):
    url: str
    title: str
    source_type: SourceType
    fetched_at: str  # ISO8601
    raw: dict[str, Any] = {}


class TopicScore(BaseModel):
    usefulness: float
    novelty: float
    dev_value: float
    search_demand: float
    monetization: float
    ease_demo: float

    @computed_field
    @property
    def total(self) -> float:
        return (
            self.usefulness + self.novelty + self.dev_value
            + self.search_demand + self.monetization + self.ease_demo
        )


class TopicCandidate(BaseModel):
    title: str
    summary: str
    source: RawSource
    score: TopicScore | None = None
    status: Literal["pending", "approved", "rejected"] = "pending"


class Claim(BaseModel):
    text: str
    source_url: str | None = None
    is_verified: bool | None = None
    verification_notes: str | None = None


class RepoInfo(BaseModel):
    full_name: str
    url: str
    stars: int = 0
    language: str | None = None
    description: str | None = None
    license: str | None = None
    readme_summary: str | None = None
    install_works: bool | None = None
    score: float | None = None
