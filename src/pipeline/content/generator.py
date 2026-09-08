import json
import re

from pipeline.agents.ollama import OllamaClient
from pipeline.db import get_db
from pipeline.models import now_iso

_PROMPT_TEMPLATE = """\
You are a social media content creator for developers. Generate a 10-slide Instagram carousel about the following AI topic.

Topic: {title}
Summary: {summary}

Return ONLY valid JSON — no explanation, no markdown, just the JSON object — with this exact structure:
{{
  "slides": [
    {{"slide": 1, "title": "...", "body": "..."}},
    {{"slide": 2, "title": "...", "body": "..."}},
    {{"slide": 3, "title": "...", "body": "..."}},
    {{"slide": 4, "title": "...", "body": "..."}},
    {{"slide": 5, "title": "...", "body": "..."}},
    {{"slide": 6, "title": "...", "body": "..."}},
    {{"slide": 7, "title": "...", "body": "..."}},
    {{"slide": 8, "title": "...", "body": "..."}},
    {{"slide": 9, "title": "...", "body": "..."}},
    {{"slide": 10, "title": "...", "body": "..."}}
  ],
  "caption": "...",
  "hashtags": ["#AI", "#developer", ...]
}}

Slide content guide:
- Slide 1: Big hook — grab attention immediately
- Slide 2: The problem — what challenge does this solve?
- Slide 3: The solution — how does this topic address it?
- Slides 4-7: Four useful tips or insights
- Slide 8: A practical example or use case
- Slide 9: Who should use this?
- Slide 10: Call to action (follow, save, share)
"""


class CarouselGenerator:
    def __init__(self, llm=None):
        self.llm = llm if llm is not None else OllamaClient()

    def generate(self, topic_id: int, title: str, summary: str, conn=None) -> dict:
        prompt = _PROMPT_TEMPLATE.format(title=title, summary=summary)
        raw = self.llm.chat(prompt)

        # Strip markdown code fences if present
        stripped = raw.strip()
        fenced = re.match(r"^```(?:json)?\s*\n(.*?)\n```\s*$", stripped, re.DOTALL)
        if fenced:
            stripped = fenced.group(1).strip()

        try:
            content = json.loads(stripped)
        except json.JSONDecodeError:
            raise ValueError(f"LLM returned invalid JSON: {raw[:200]}")

        hook = content["slides"][0]["body"]
        content_json = json.dumps(content)
        created_at = now_iso()

        if conn is None:
            conn = get_db()

        conn.execute(
            "INSERT INTO posts (topic_id, format, hook, content_json, status, created_at) "
            "VALUES (?, 'carousel', ?, ?, 'pending_approval', ?)",
            (topic_id, hook, content_json, created_at),
        )
        conn.commit()

        return content
