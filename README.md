# RESEATCH_PIPELINE — AI Social Media Pipeline

A fully local, zero-cost pipeline that researches AI tools daily, scores them, generates social media content, and posts automatically — with a human approval step in between.

Built by [Anshu](https://github.com/jaiswal00007) · Follow me.

---

## What it does

```
GitHub + HN + RSS + arXiv + Product Hunt
            ↓
     Research Agent (local LLM)
            ↓
     Validation Agent (local LLM)
            ↓
     Scorer (6 dimensions, 0–60)
            ↓
     Content Generator → 10-slide carousel
            ↓
     You review in terminal (approve / reject)
            ↓
     Auto-post to Instagram + YouTube
```

Runs entirely on your machine. No OpenAI. No cloud costs.

---

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) — `pip install uv`
- [Ollama](https://ollama.com) with `qwen3:8b` pulled

```bash
ollama pull qwen3:8b
```

---

## Setup

```bash
git clone https://github.com/jaiswal00007/research-pipeline
cd devtoolsai
uv sync
cp .env.example .env
```

Edit `.env` with your credentials (see below).

---

## Commands

| Command | What it does |
|---|---|
| `uv run pipeline` | Fetch sources, research, validate, score, save approved topics |
| `uv run workflow` | Generate carousel content for approved topics |
| `uv run approve` | Review pending posts in terminal |
| `uv run post` | Publish approved posts to Instagram + YouTube |
| `uv run post --dry-run` | Preview what would be posted without calling any API |

### Full daily flow

```bash
uv run pipeline     # ~5 min — finds and scores today's AI topics
uv run workflow     # ~2 min — generates carousel content
uv run approve      # ~10 min — you review and approve
uv run post         # seconds — publishes to social media
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in:

```bash
# GitHub (optional — raises rate limit from 60 to 5,000 req/hr)
GITHUB_TOKEN=

# Ollama (default: local)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:8b

# Database
DB_PATH=pipeline.db

# Instagram (required for posting)
INSTAGRAM_ACCESS_TOKEN=
INSTAGRAM_ACCOUNT_ID=

# YouTube (required for posting)
YOUTUBE_API_KEY=
```

**Getting Instagram credentials:**
1. Create a Professional Instagram account (Business or Creator)
2. Link it to a Facebook Page
3. Create an app at [developers.facebook.com](https://developers.facebook.com)
4. Add Instagram API with Facebook Login → generate token with `instagram_basic` + `instagram_content_publish`
5. Get your account ID via Graph API Explorer: `GET /{page_id}?fields=instagram_business_account`

**Getting YouTube API key:**
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Enable YouTube Data API v3
3. Create an API key under Credentials

---

## Scoring

Each topic is scored across 6 dimensions (0–10 each, max 60):

| Dimension | What it measures |
|---|---|
| Usefulness | Will devs actually use this? |
| Novelty | Is this genuinely new? |
| Dev Value | Does it save time or unlock capability? |
| Search Demand | Are people looking for this? |
| Monetization | Can you build something with it? |
| Ease of Demo | Can you show it in 60 seconds? |

Topics scoring below **35/60** are automatically rejected.

---

## Sources

| Source | Type | Requires key? |
|---|---|---|
| GitHub Trending | Repos | No (optional token for higher rate limit) |
| Hacker News | Stories | No |
| RSS Feeds | Blog posts | No |
| arXiv | Papers | No |
| Product Hunt | AI launches | No |
| DuckDuckGo | Web search | No |

All sources are free. The pipeline runs without any API keys (GitHub token is optional).

---

## Project Structure

```
src/pipeline/
  agents/
    ollama.py         # Ollama LLM client
    researcher.py     # Summarises raw sources
    validator.py      # Fact-checks summaries
  cli/
    approve.py        # Terminal approval workflow
  content/
    generator.py      # Carousel content generation
    poster.py         # Instagram + YouTube publishing
  sources/
    arxiv.py          # arXiv papers
    brave.py          # DuckDuckGo web search
    github.py         # GitHub trending
    hackernews.py     # HN top stories
    producthunt.py    # Product Hunt RSS
    rss.py            # AI company blogs
  db.py               # SQLite setup
  http.py             # HTTP client with retry logic
  models.py           # Pydantic data models
  runner.py           # Research pipeline
  scorer.py           # Topic scoring
  workflow.py         # Content + posting workflow
tests/                # 62 tests
```

---

## Running Tests

```bash
uv run pytest tests/ -v
```

All 62 tests pass with no external API calls (fully mocked).

---

## What's next

- [ ] Auto-generate slide images (Stable Diffusion / DALL-E)
- [ ] Analytics feedback loop — tune scoring from engagement data
- [ ] LinkedIn, X/Twitter, Threads support
- [ ] Instagram token auto-refresh (tokens expire every 60 days)
- [ ] n8n workflow integration

---

## License

MIT
