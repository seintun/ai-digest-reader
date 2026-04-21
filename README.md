# DailyDigest

Automated AI news digest aggregating content from Reddit, Hacker News, and RSS feeds — with AI-powered summaries via OpenRouter and a mobile-first PWA reader.

## Features

- **Multi-source aggregation** — 24 Reddit subs + HN front page + 14 RSS feeds (TechCrunch, Wired, TLDR, The Batch, Import AI, ArXiv AI/ML, and more)
- **AI summaries** — Powered by OpenRouter (`moonshotai/kimi-k2`) with Claude CLI fallback; produces themes, breaking news, must-reads, and a full brief
- **Story categories** — AI & ML, Tech, Security, Science, World News, Business, Futurology, Startups
- **Schema v4** — Ranked stories, content-quality metadata, optional RSS stories, run metrics
- **Automation** — GitHub Actions runs twice daily (7am + 6pm UTC); manual trigger also available
- **PWA reader** — Mobile-first Astro site with search, category filters, bookmarks, dark mode, offline support

## Quick Start

```bash
# 1. Clone and run setup
git clone <repo-url> dailydigest
cd dailydigest
./scripts/setup.sh

# 2. Add your OpenRouter key
echo "OPENROUTER_API_KEY=sk-or-v1-..." >> .env

# 3. Generate today's digest
source .venv/bin/activate
python digest.py

# 4. Preview the reader
cd ai-digest-reader
npm run dev
```

## Setup

### Prerequisites

- Python 3.8+
- Node 18+
- An [OpenRouter](https://openrouter.ai) API key (for AI summaries)

### One-command setup

```bash
./scripts/setup.sh
```

This creates a Python venv, installs all dependencies (Python + npm), and copies `.env.example` to `.env`.

### Manual setup

```bash
# Python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Frontend
cd ai-digest-reader && npm install

# Environment
cp .env.example .env
# Edit .env and add OPENROUTER_API_KEY
```

## Usage

### Generate a digest

```bash
source .venv/bin/activate

# Full run with AI summary
python digest.py

# Skip AI (faster, no API key needed)
python digest.py --no-ai

# Limit posts per source
python digest.py --limit 5

# Custom output directory
python digest.py --output-dir ./my-digests/

# Specific subreddits only
python digest.py --subreddits ArtificialIntelligence LocalLLaMA
```

### Deploy to the reader

```bash
# Copy latest digest to the frontend
cp output/$(date +%Y-%m-%d)/digest.json ai-digest-reader/public/data/digest.json

# Build and preview
cd ai-digest-reader
npm run build && npm run preview
```

Or use the automated script:

```bash
./scripts/generate-and-deploy.sh
```

This runs the digest, copies JSON, builds the site, and commits + pushes.

## Automation

### GitHub Actions (recommended)

Set the following repository secrets:

| Secret | Description |
|--------|-------------|
| `OPENROUTER_API_KEY` | OpenRouter API key |
| `VERCEL_TOKEN` | Vercel deploy token |
| `VERCEL_ORG_ID` | Vercel org ID |
| `VERCEL_PROJECT_ID` | Vercel project ID |

The workflow (`.github/workflows/daily-digest.yml`) runs at 07:00 and 18:00 UTC. Trigger manually via **Actions → Daily Digest → Run workflow**.

### Local cron

```bash
./scripts/cron-install.sh
```

Installs crontab entries to run `generate-and-deploy.sh` at 7am and 6pm.

## Output

```
output/
└── 2026-04-20/
    ├── digest-2026-04-20-070000.md    ← Human-readable digest
    ├── digest.json                    ← Structured data (v4 schema)
    ├── metrics.json                   ← Runtime/scrape/cost metrics
    └── monitoring-dashboard.md        ← Markdown monitoring dashboard
```

### digest.json schema (v4)

```json
{
  "v": 4,
  "d": "2026-04-20",
  "g": "2026-04-20T07:00:00",
  "r": [ /* Reddit stories */ ],
  "h": [ /* HN stories */ ],
  "rs": [ /* RSS stories */ ],
  "metrics": {
    "runtime": {"total_seconds": 72.4, "within_budget": true},
    "scraping": {"candidate_urls": 40, "success_rate": 82.5, "cache_hit_rate": 35.0},
    "ranking": {"total_posts": 120, "llm_quality_used": true},
    "summary": {"source": "openrouter", "generated": true},
    "cost": {"estimated_usd": 0.17, "within_budget": true},
    "degradation": {
      "scraping_fallback_used": false,
      "ranking_fallback_used": false,
      "summary_fallback_used": false,
      "no_summary_fallback_used": false
    }
  },
  "summary": {
    "schema_version": "2",
    "simple": "2-3 sentence TL;DR",
    "structured": {
      "themes": ["Theme 1", "Theme 2", "Theme 3"],
      "breaking": "Most significant story.",
      "mustRead": [{ "id": "rd-0", "title": "...", "url": "...", "reason": "..." }]
    },
    "fullBrief": {
      "intro": "...",
      "sections": [{ "heading": "...", "body": "..." }],
      "closing": "..."
    }
  }
}
```

Each story object:

| Key | Type | Description |
|-----|------|-------------|
| `i` | string | ID with prefix: `rd-N` (Reddit), `hn-N` (HN), `rs-N` (RSS) |
| `t` | string | Title |
| `u` | string | Article URL |
| `p` | string | Discussion permalink |
| `b` | string | Body excerpt (max ~280 chars) |
| `s` | number | Score / upvotes |
| `c` | number | Comment count |
| `a` | string | Author |
| `cat` | string | Category: `AI & ML`, `Tech`, `Security`, `Science`, `World News`, `Business`, `Futurology`, `Startups` |
| `rank` | number | Importance score (0-100) |
| `content_available` | boolean | Whether full article content was scraped |
| `content_quality` | number | LLM-rated substance score (1-10, or 0 when fallback used) |
| `excerpt` | string | First 200 chars of scraped content (or body fallback) |

## Degradation Procedures

The pipeline degrades safely in this order when dependencies fail:

1. **Full pipeline**: scraping + ranking + content-aware summary.
2. **Scraping fallback**: if content extraction fails for a URL, ranking uses post snippets.
3. **Ranking fallback**: if LLM quality scoring fails, ranking uses engagement + recency + cross-source only.
4. **Summary fallback**: if `analyzer_v2` fails, fallback to legacy `analyzer.py`.
5. **No-summary fallback**: if all LLM paths fail, digest still outputs stories without `summary`.

Every run records which fallback paths were used in `digest.json.metrics.degradation`.

## Sources

**Reddit** (24 subreddits)

| Subreddit | Category |
|-----------|----------|
| r/ArtificialIntelligence | AI & ML |
| r/LocalLLaMA | AI & ML |
| r/ChatGPT | AI & ML |
| r/MachineLearning | AI & ML |
| r/singularity | AI & ML |
| r/artificial | AI & ML |
| r/OpenAI | AI & ML |
| r/ClaudeAI | AI & ML |
| r/GeminiAI | AI & ML |
| r/technology | Tech |
| r/programming | Tech |
| r/ExperiencedDevs | Tech |
| r/selfhosted | Tech |
| r/devops | Tech |
| r/netsec | Security |
| r/science | Science |
| r/space | Science |
| r/EverythingScience | Science |
| r/worldnews | World News |
| r/geopolitics | World News |
| r/startups | Startups |
| r/YCombinator | Startups |
| r/economics | Business |
| r/Futurology | Futurology |

**Hacker News** — Front page (Tech)

**RSS Feeds** (14 feeds)

| Feed | Category |
|------|----------|
| TechCrunch | Tech |
| The Verge | Tech |
| Ars Technica | Tech |
| Wired | Tech |
| Slashdot | Tech |
| ArXiv CS.AI | AI & ML |
| ArXiv CS.LG | AI & ML |
| MIT Tech Review | Tech |
| BBC Technology | Tech |
| Reuters Technology | World News |
| TLDR Tech | Tech |
| TLDR AI | AI & ML |
| The Batch (DeepLearning.AI) | AI & ML |
| Import AI (Jack Clark) | AI & ML |

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/setup.sh` | One-time setup: venv, deps, .env |
| `scripts/generate-and-deploy.sh` | Full pipeline: generate → copy → build → push |
| `scripts/cron-install.sh` | Install local crontab for scheduled runs |
| `digest.py` | Main entry point |
| `analyzer.py` | OpenRouter AI summarization (Kimi K2 + Claude CLI fallback) |
| `schema.py` | TypedDict contracts + validators for v2/v3 schema |
| `fetchers/` | Reddit, HN, and RSS API integration |
| `formatter.py` | Markdown output formatting |
| `config.py` | Subreddits, RSS feeds, categories, limits |

## Tests

```bash
source .venv/bin/activate
PYTHONPATH=$(pwd) pytest tests/ -v
```

100 tests covering fetchers, schema validation, config, RSS parsing, and source expansion.

## Troubleshooting

See [ai-digest-reader/docs/TROUBLESHOOTING.md](ai-digest-reader/docs/TROUBLESHOOTING.md).
