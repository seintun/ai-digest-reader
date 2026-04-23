# Quality-First Overhaul — Design Spec

**Date**: 2026-04-22  
**Branch**: `feat/quality-overhaul`  
**Status**: Implemented

---

## Problem Statement

The DailyDigest pipeline produced a working digest but had three quality-limiting problems:

1. **Ranking favored stale content** — raw upvote score with no age penalty meant a 22h-old viral post outranked a 2h-old high-quality story.
2. **Token-heavy, noisy prompts** — summarization sent up to 2000 chars of raw scraped text per story (30KB+ per run), reducing LLM signal-to-noise ratio.
3. **Duplicated, fragile LLM layer** — `analyzer.py` and `analyzer_v2.py` both wrapped OpenRouter + Claude CLI with divergent logic; `ranker.py` used a `curl` subprocess with no connection reuse.

---

## Four Pillars

### Pillar 1 — Ranking Quality

**Files changed**: `ranker.py`

#### Cross-source matching: O(n²) → O(n)

**Before**: nested loop comparing every post URL pair — 14,400 comparisons for 120 posts.

**After**: build a dict keyed by `sha256(domain + path)`. Group posts by canonical key in one pass; assign cross-source counts from group sizes.

```
Before: O(n²) = 14,400 ops for 120 posts
After:  O(n)  = 120 ops for 120 posts
```

#### Freshness-adjusted engagement

**Before**: raw `score / 5000 * 20` — age-blind.

**After**: `score * (1 / sqrt(age_hours + 1)) / 2000 * 18` — penalizes older posts geometrically.

#### Rebalanced signal weights

| Signal | Before | After | Max pts |
|--------|--------|-------|---------|
| Engagement (freshness-adjusted) | 40% | 30% | 30 |
| Recency | 15% | 15% | 15 |
| Cross-source | 15% | 20% | 20 |
| Content quality | 30% | 35% | 35 |
| **Total** | 100% | 100% | **100** |

Quality and story convergence now drive ranking rather than raw upvote counts.

---

### Pillar 2 — Prompt Engineering

**Files changed**: `schema.py`, `analyzer_v2.py`, `ranker.py`

#### `extract_excerpt(content, max_chars=200)` — new shared utility in `schema.py`

- Strips HTML tags
- Collapses whitespace
- Truncates at last sentence boundary ≤ `max_chars`
- Used by ranker (150 chars) and summarizer (200 chars)

#### Compact story block format

Both ranking and summarization prompts now use:
```
[{story_id}] [{rank}/100] {title} | src:{source} | age:{h}h | score:{n} | quality:{q}/10
url: {url}
excerpt: "{200-char clean excerpt}"
```

#### System prompt carries output schema

The JSON output schema was moved from the user-turn into the `system` message — sent once per API call, not repeated per story. Saves ~200 tokens per call.

#### Token reduction

| Prompt | Before | After | Savings |
|--------|--------|-------|---------|
| Summarization (15 stories) | ~30,000 tokens | ~9,000 tokens | **~70%** |
| Ranking quality (per story) | ~800 tokens | ~120 tokens | **~85%** |

---

### Pillar 3 — LLM Layer Consolidation

**Files changed**: new `llm_client.py`, rewritten `analyzer_v2.py`, `ranker.py`  
**Files deleted**: `analyzer.py`

#### New `llm_client.py`

Single `LLMClient` class replacing all three previous LLM integration points:

```
LLMClient
  ├── __init__(model, api_key, connect_timeout, read_timeout, cli_timeout)
  ├── complete(prompt, system=None) → (content | None, usage_dict)
  │     ├── in-memory cache: sha256(system+prompt) → skip API call entirely
  │     ├── OpenRouter via requests.Session (persistent connection pool)
  │     ├── retry once on failure with 2s backoff
  │     └── Claude CLI fallback on second failure
  └── _cli_fallback(prompt, cache_key)
```

Key improvements over old curl subprocess approach:
- **Connection pool**: `requests.Session` reuses TCP connections — no process spawn overhead
- **Cache**: identical prompts within a run cost $0 on repeat
- **Single retry strategy**: consistent 2s backoff, not divergent per-module logic
- **No shell injection risk**: no subprocess with user-controlled strings

#### `analyzer_v2.py` — thin shim (~100 lines)

Now builds a compact prompt and calls `LLMClient.complete(prompt, system=_SYSTEM_PROMPT)`. No HTTP code, no subprocess, no retry logic.

#### `analyzer.py` — deleted

270 lines of duplicated HTTP + retry + prompt logic removed entirely.

---

### Pillar 4 — Surgical Fixes

| Fix | File | Impact |
|-----|------|--------|
| `CREATE INDEX IF NOT EXISTS idx_url_hash` on SQLite cache | `scraper.py` | Cache lookups O(1) instead of full table scan |
| Parallel Reddit fetching (`ThreadPoolExecutor(max_workers=8)`) | `digest.py` | 24–48s → 6–12s fetch time |
| Remove unused `openai` package | `requirements.txt` | Cleaner deps, faster installs |
| Centralize timeouts/limits in `config.py` with env override | `config.py`, `scraper.py` | All tuning knobs in one place |
| `parse_llm_json` shared in `schema.py` | `schema.py`, `ranker.py` | No duplicated JSON parser logic |

---

## Architecture Diagrams

### Before

```
digest.py
├── fetch_reddit_posts() × 24  [sequential, ~30s]
├── fetch_hn_posts()
├── fetch_all_rss_feeds()
├── scrape_articles_with_stats()
│   └── SQLite cache [no index, O(n) lookup]
├── ranker.py
│   ├── _compute_cross_source_scores() [O(n²)]
│   ├── _engagement_points() [age-blind]
│   └── _request_quality_ratings()
│       └── subprocess curl → OpenRouter [new process per batch]
├── analyzer_v2.py
│   ├── _build_prompt() [2000 chars/story × 15 = 30KB+]
│   ├── analyzer._call_openrouter_with_usage() [curl subprocess]
│   └── analyzer._call_claude_cli() [subprocess]
└── analyzer.py [270 lines, duplicate fallback chain]
```

### After

```
digest.py
├── fetch_reddit_posts() × 24  [parallel, ThreadPoolExecutor(8), ~8s]
├── fetch_hn_posts()
├── fetch_all_rss_feeds()
├── scrape_articles_with_stats()
│   └── SQLite cache [idx_url_hash index, O(1) lookup]
├── ranker.py
│   ├── _compute_cross_source_scores() [O(n), hash bucket]
│   ├── _engagement_points() [freshness-adjusted]
│   └── _request_quality_ratings(batch, client)
│       └── LLMClient.complete() [requests.Session pool, cached]
├── analyzer_v2.py
│   ├── _build_prompt() [200 chars/story × 15 = ~3KB]
│   └── LLMClient.complete(prompt, system=_SYSTEM_PROMPT)
└── llm_client.py [single source of truth for all LLM calls]
    ├── requests.Session [persistent TCP pool]
    ├── in-memory cache [sha256 keyed]
    ├── 1 retry + 2s backoff
    └── Claude CLI fallback
```

---

## Estimated Savings

| Area | Before | After | Savings |
|------|--------|-------|---------|
| Summarization prompt tokens | ~30,000 / run | ~9,000 / run | ~70% |
| Ranking prompt tokens (per story) | ~800 tokens | ~120 tokens | ~85% |
| Reddit fetch time | 24–48s (sequential) | 6–12s (8 parallel) | ~75% |
| Cross-source match ops | O(n²) = 14,400 for 120 posts | O(n) = 120 ops | ~99% |
| LLM API connections | new process per batch (curl) | persistent session pool | latency −30–50% |
| Duplicate LLM calls (same prompt) | billed each time | cached within run | up to 100% |
| Est. cost per run | ~$0.20–0.25 | ~$0.07–0.12 | ~50–60% |
| Est. total pipeline time | 3–5 min | 1.5–3 min | ~40–50% |

*Cost savings assume Kimi K2.6 pricing. Quality improvement is the primary goal.*

---

## Files Changed

| File | Action |
|------|--------|
| `schema.py` | Added `extract_excerpt()`, `parse_llm_json()` |
| `llm_client.py` | **New** — unified LLM wrapper |
| `ranker.py` | Refactored: LLMClient, hash cross-source, freshness score, rebalanced weights, compact prompt |
| `analyzer_v2.py` | Rewritten: thin shim + compact prompt + system prompt |
| `analyzer.py` | **Deleted** |
| `scraper.py` | Added SQLite index, imported config constants |
| `digest.py` | Parallelized Reddit fetching, removed v1 fallback |
| `config.py` | Centralized timeouts/limits with env override |
| `requirements.txt` | Removed `openai` |
| `tests/test_schema.py` | Added 14 tests for new utilities |
| `tests/test_llm_client.py` | **New** — 7 LLMClient unit tests |
| `tests/test_analyzer_v2.py` | Rewritten for new API |
| `tests/test_analyzer.py` | Redirected (analyzer.py deleted) |

**Frontend**: untouched  
**GitHub Actions**: untouched  
**digest.json schema**: backwards compatible
