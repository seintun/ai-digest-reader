# DailyDigest

Automated AI news digest aggregating content from Reddit, Hacker News, and RSS feeds — with AI-powered summaries via OpenRouter and a mobile-first PWA reader.

## Features

- **Multi-source aggregation** — 24 Reddit subs + HN front page + 13 RSS feeds (TechCrunch, Wired, TLDR, The Batch, Import AI, ArXiv AI/ML, and more)
- **Resilient fetching** — Reddit recovers via Atom RSS when the JSON API is blocked (401/403/429); article extraction tries defuddle first, then a trafilatura → readability → lxml → metadata → Jina → archive.today chain
- **Extraction telemetry** — every run records which extractor won each URL and why others fell through (`metrics.scraping.extractor_breakdown`)
- **HN discussion context** — top HN stories are enriched with their top comments (Algolia) so the summary sees community signal, not just titles
- **AI summaries + analysis** — schema-v2 summary (TL;DR, themes, breaking, must-read, full brief) plus an optional stage-3 devil's-advocate analysis (implications, skeptic's take, confidence, evidence basis)
- **Evidence-aware prompting** — stories are tagged `verified-content` vs `title-only` so the model doesn't invent specifics for unscraped items
- **Story categories** — AI & ML, Tech, Security, Science, World News, Business, Futurology, Startups
- **Schema v4** — Ranked stories, content-quality metadata, RSS stories, run metrics, quality block
- **Quality gate** — soft regression gate warns when scrape success drops or the summary fails repeatedly; surfaced to Discord via the cron report
- **Automation** — Hermes cron runs twice daily at 8am and 5pm Pacific; GitHub Actions scheduling has been removed
- **PWA reader** — Mobile-first Astro site with search, category filters, bookmarks, dark mode, offline support, and a collapsible Analysis & Implications panel

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
- An [OpenRouter](https://openrouter.ai) API key (for AI summaries) — or a Hermes CLI for the Hermes summary/analysis provider
- (Optional) [`defuddle`](https://www.npmjs.com/package/defuddle) CLI on `PATH` — preferred article extractor. Without it, the pipeline falls back to the trafilatura chain automatically. Override the binary path with `DEFUDDLE_BIN`.

### One-command setup

```bash
./scripts/setup.sh
```

This creates a Python venv, installs all dependencies (Python + npm), and copies `.env.example` to `.env`.

### Required environment

`OPENROUTER_API_KEY` is required for:
- content-quality ranking in `ranker.py`
- AI summary generation (`analyzer_v2.py`, fallback `analyzer.py`)

Without it, digest generation still works with ranking/summarization fallbacks.

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

### Run End-to-End Locally

```bash
# 1) Generate digest artifacts
source .venv/bin/activate
python digest.py

# 2) Copy latest digest into reader public data
cp output/$(date +%Y-%m-%d)/digest.json ai-digest-reader/public/data/digest.json

# 3) Start frontend
cd ai-digest-reader
npm install
npm run dev
```

### Generated Artifacts Per Run

- `digest.json` — v4 digest payload with ranked stories and summary
- `metrics.json` — runtime, scraping, ranking, summary, and cost metrics
- `monitoring-dashboard.md` — markdown dashboard for quick run inspection
- `digest-<date>-<time>.md` — human-readable markdown digest

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

### Hermes cron

Production scheduling is owned by Hermes (not GitHub Actions). The schedule is 8:00 AM and 5:00 PM Pacific. Hermes invokes [`scripts/hermes-digest-run.sh`](scripts/hermes-digest-run.sh) with these environment variables:

```bash
AI_DIGEST_ENGINE=openclaw \
AI_DIGEST_OPENCLAW_STAGES=summary,notebooklm_ingest \
AI_DIGEST_SUMMARY_PROVIDER=hermes \
AI_DIGEST_REQUIRE_SUMMARY=1 \
AI_DIGEST_RANKER_PROVIDER=openclaw \
RANKER_AI_ENABLED=1 \
AI_DIGEST_HERMES_PROVIDER=omniroute \
AI_DIGEST_HERMES_MODEL=codex-combo \
AI_DIGEST_ANALYSIS_ENABLED=1 \
bash ./scripts/hermes-digest-run.sh --full
```

The wrapper runs the pipeline, validates the digest, writes the summary/benchmark report, and runs the quality gate. It emits a final single-line JSON report (status, digest path, quality-gate warnings) that the Hermes cron agent uses to post a rich Discord message: TL;DR, breaking headline, top-3 must-read links, the analysis (when present), and any quality-gate warnings. Supported modes: `--full`, `--validate-only`, `--check-only`. The runbook is [`scripts/openclaw-cron-run.md`](scripts/openclaw-cron-run.md).

### Legacy local crontab

`scripts/cron-install.sh` is kept for manual machine crontab installs, but Hermes cron is preferred because it can use model routing, the analysis stage, and report failures/quality warnings to Discord.

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
    "scraping": {
      "candidate_urls": 40, "success_rate": 82.5, "cache_hit_rate": 35.0,
      "extractor_breakdown": {
        "defuddle": 28, "trafilatura": 4, "cache": 6, "none": 2,
        "failure_reasons": {"defuddle:no_output": 6, "fetch:http_403": 2}
      }
    },
    "ranking": {"total_posts": 120, "llm_quality_used": true},
    "summary": {"source": "hermes", "generated": true},
    "analysis": {"source": "analysis", "generated": true, "confidence": "medium"},
    "quality": {
      "total_stories": 160, "stories_with_content": 10,
      "content_coverage_pct": 6.2, "scrape_success_rate": 95.0,
      "scrape_candidate_urls": 40,
      "source_counts": {"reddit": 20, "hackernews": 10, "rss": 130},
      "analysis_generated": true
    },
    "cost": {
      "pricing_source": "OpenRouter response usage accounting",
      "session_model_usd": 0.021384,
      "within_budget": true
    },
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
    },
    "analysis": {
      "implications": ["what this means for engineers", "what this means for the industry"],
      "skeptic_take": "strongest counter-argument",
      "confidence": "high | medium | low",
      "evidence_basis": ["which claims are verified", "which are title-only"]
    }
  }
}
```

> **Notes on the metrics:**
> - `scraping.extractor_breakdown` counts which extractor produced each URL's
>   content (`defuddle`/`trafilatura`/`readability`/`lxml`/`metadata`/`jina`/
>   `archive`/`cache`), how many fell through to `none`, and a `failure_reasons`
>   map of `stage:reason` pairs.
> - `quality.content_coverage_pct` is the % of *all* stories with scraped content
>   (informational; structurally low because most RSS/Reddit items aren't scrape
>   candidates). `quality.scrape_success_rate` is the % of *attempted* URLs that
>   returned content (cache-inclusive) — this is what the quality gate watches.
> - `summary.analysis` is only present when `AI_DIGEST_ANALYSIS_ENABLED=1`.

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
| `content_quality` | number | LLM-rated substance score (1-10), title-heuristic fallback when unscraped |
| `excerpt` | string | First ~400 chars of scraped content (or body fallback) |
| `discussion_context` | array | (HN only) Top comments: `[{author, text, depth}]`, when enrichment is enabled |

## Degradation Procedures

The pipeline degrades safely in this order when dependencies fail:

1. **Full pipeline**: defuddle-first scraping + ranking + content-aware, evidence-tagged summary + optional analysis.
2. **Reddit fetch fallback**: if the Reddit JSON API returns 401/403/429, the fetcher recovers via the Atom RSS feed (titles/URLs, no scores).
3. **Extraction fallback chain**: for each URL, defuddle → HTTP fetch + trafilatura → readability → lxml → metadata → Jina proxy → archive.today. Each fallthrough is recorded in `extractor_breakdown`.
4. **Ranking fallback**: if LLM quality scoring fails or a story has no scrapeable content, ranking uses a title heuristic plus engagement + recency + cross-source signals.
5. **Summary fallback**: if the configured summary provider fails, the digest still outputs stories without `summary` (and the quality gate flags repeated failures).
6. **Analysis is best-effort**: if the stage-3 analysis fails, the summary is still emitted without an `analysis` block.

Every run records which fallback paths were used in `digest.json.metrics.degradation`, extraction outcomes in `metrics.scraping.extractor_breakdown`, and coverage/health in `metrics.quality`. Per-run model spend is recorded in `metrics.cost.session_model_usd`.

The **quality gate** (`scripts/quality_gate.py`) runs after each successful run and warns (without blocking) when scrape success drops below threshold or the summary fails for consecutive runs. Warnings are surfaced to Discord by the Hermes cron report.

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

**RSS Feeds** (13 feeds)

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
| TLDR Tech | Tech |
| TLDR AI | AI & ML |
| The Batch (DeepLearning.AI) | AI & ML |
| Import AI (Jack Clark) | AI & ML |

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/setup.sh` | One-time setup: venv, deps, .env |
| `scripts/generate-and-deploy.sh` | Full pipeline: generate → copy → build → push |
| `scripts/hermes-digest-run.sh` | Hermes-owned wrapper: run → validate → benchmark report → quality gate |
| `scripts/quality_gate.py` | Soft quality-regression gate (scrape success + repeated summary failures) |
| `scripts/write_summary_benchmark_report.py` | Writes the daily summary/benchmark report |
| `scripts/validate-digest.py` | Validates digest JSON against the v4 envelope + summary schema |
| `scripts/cron-install.sh` | Install local crontab for scheduled runs (legacy) |
| `digest.py` | Main entry point |
| `analyzer_v2.py` | Content-aware, evidence-tagged summary generation |
| `analyzer.py` | Legacy summary fallback (OpenRouter + Claude CLI) |
| `engine/analysis.py` | Stage-3 devil's-advocate analysis (implications/skeptic/confidence) |
| `engine/summary.py` | Summary provider routing (OpenClaw / Hermes / benchmark) |
| `engine/config.py` | Engine + summary provider configuration |
| `ranker.py` | Multi-signal ranking with LLM quality + title-heuristic fallback |
| `scraper.py` | defuddle-first scraping, fallback extraction chain, telemetry, SQLite cache |
| `pipeline_metrics.py` | Runtime/cost metrics and monitoring dashboard renderer |
| `schema.py` | TypedDict contracts + validators for v2/v3/v4 schema |
| `fetchers/` | Reddit (JSON + RSS fallback), HN (+ top comments), and RSS integration |
| `formatter.py` | Markdown output formatting |
| `config.py` | Subreddits, RSS feeds, categories, limits |

## Tests

```bash
source .venv/bin/activate
PYTHONPATH=$(pwd) pytest tests/ -v
```

197 tests covering fetchers, scraper (defuddle + telemetry), ranker, schema
validation, config, RSS parsing, the analysis stage, the quality gate, and the
benchmark report.

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `OPENROUTER_API_KEY` | — | OpenRouter key for ranking/summary (standalone mode) |
| `AI_DIGEST_ENGINE` | `standalone` | `standalone` or `openclaw` |
| `AI_DIGEST_SUMMARY_PROVIDER` | `hermes` | `legacy` / `openclaw` / `hermes` / `benchmark` |
| `AI_DIGEST_ANALYSIS_ENABLED` | `0` | Set `1` to run the stage-3 analysis |
| `AI_DIGEST_HN_COMMENT_STORIES` | `10` | Top-N HN stories enriched with comments (`0` disables) |
| `AI_DIGEST_SUMMARY_EXCERPT_CHARS` | `400` | Excerpt length fed to the summary prompt |
| `DEFUDDLE_BIN` | `/Users/.../defuddle` | Path to the defuddle CLI |
| `SCRAPER_DEFUDDLE_TIMEOUT` | `12` | defuddle per-URL timeout (seconds) |
| `REDDIT_RSS_FALLBACK_ON_TERMINAL` | `1` | Recover via RSS when Reddit JSON is blocked |
| `REDDIT_GLOBAL_BLOCK_PROBE` | `0` | Re-enable the global Reddit block short-circuit |
| `RANKER_AI_ENABLED` | `1` | Enable LLM content-quality scoring |

## Troubleshooting

See [ai-digest-reader/docs/TROUBLESHOOTING.md](ai-digest-reader/docs/TROUBLESHOOTING.md).
