# Technical Architecture

## Data Flow

1. `digest.py` orchestrates Reddit, HN, and RSS fetchers, normalizes payloads, and builds a unified post list.
2. `scraper.py` selects top candidates (`score > 10 OR comments > 5`, max 40), scrapes article content with cache + fallbacks.
3. `ranker.py` scores posts with engagement, recency, cross-source matching, and optional LLM content quality.
4. `analyzer_v2.py` summarizes the top 15 ranked stories with content-aware prompts.
5. `digest.py` writes:
   - `output/<date>/digest.json` (v4 data + metrics)
   - `output/<date>/metrics.json` (monitoring metrics)
   - `output/<date>/monitoring-dashboard.md` (human-readable dashboard)
6. `ai-digest-reader/public/data/digest.json` is consumed by the Astro frontend.
7. Frontend merges all sources and sorts globally by `rank` (fallback to score), so users see most important stories first.

## Security and Validation Hardening

- Frontend story rendering now escapes all untrusted text fields (`title`, `body`, `author`) before DOM insertion.
- External links use protocol allowlisting (`http`/`https`) to block scriptable URL schemes.
- `schema.validate_summary()` uses explicit conditional validation instead of `assert` checks, so behavior is stable even under optimized Python execution.
- Summary validation enforces `fullBrief.sections` bounds of `2-4` sections to align with the contract.

## Runtime and Efficiency Improvements

- Frontend renders only the active view (`cards`, `list`, `glance`) per update, instead of rendering all three and hiding two.
- Controls initialization is guarded to prevent duplicate event listener registration.
- Hacker News fetcher now loads item payloads with bounded parallelism (`ThreadPoolExecutor`) to reduce end-to-end latency.
- Reddit fetcher consolidates payload extraction/normalization in dedicated helpers to reduce duplicate logic and maintenance overhead.
- Markdown formatter emits correct HN links (`[link](url)`) instead of malformed score-based links.

## Codebase Simplification

- Removed unused frontend modules that were not referenced by runtime code:
  - `ai-digest-reader/src/lib/state.ts`
  - `ai-digest-reader/src/lib/digest.ts`
  - `ai-digest-reader/src/components/StoryCard.astro`
  - `ai-digest-reader/src/components/StoryList.astro`
  - `ai-digest-reader/src/components/StoryGlance.astro`
  - `ai-digest-reader/src/components/ViewSwitcher.astro`
  - `ai-digest-reader/src/components/SourceFilter.astro`
- Removed stale unused interfaces from `ai-digest-reader/src/types.ts`.

## Story Schema (v4)

Each story uses compact keys:

- `i`: stable id (`rd-<index>`, `hn-<index>`, or `rs-<index>`)
- `t`: title
- `u`: external/original article URL
- `p`: discussion permalink (Reddit thread or HN item URL)
- `b`: optional body excerpt (plain text)
- `s`: score/upvotes
- `c`: comment count
- `a`: author
- `rank`: 0-100 importance score
- `content_available`: boolean scrape availability flag
- `content_quality`: LLM quality score (1-10, `0` when fallback used)
- `excerpt`: first 200 chars of scraped content (or body fallback)

## Link Routing Rules

- Primary card/title click navigates to `p || u` in the same tab.
- Secondary external link uses `u` in the same tab when `u !== p`.
- This preserves swipe-back behavior on mobile browsers.

## Ranking Strategy

- **Engagement (40%)**: normalized score + comments.
- **Content quality (30%)**: batched LLM rating on 200-char excerpts.
- **Recency (15%)**: exponential decay with 24-hour half-life.
- **Cross-source (15%)**: same-story detection across Reddit/HN/RSS via domain+path similarity.

Fallback behavior:
- If scraping fails for a URL: use post body/snippet.
- If LLM quality fails: use engagement + recency + cross-source only.
- If content-aware summarization fails: fallback to legacy analyzer.
- If all summary paths fail: emit digest without summary.

## Mobile UX Decisions

- Card and list interactions avoid `target="_blank"`.
- Touch targets are increased for better tap accuracy.
- List view switches to stacked cards on narrow screens to eliminate horizontal scrolling.
- Optional body excerpts improve skimmability without AI-generated copy.

---

## 2026-04 Quality-First Overhaul

Full design spec: [`docs/superpowers/specs/2026-04-22-quality-first-overhaul-design.md`](superpowers/specs/2026-04-22-quality-first-overhaul-design.md)

### New module: `llm_client.py`

Replaces the three previous LLM integration points (`analyzer.py` curl, `analyzer_v2.py` curl, `ranker.py` curl). Single `LLMClient` class with:
- `requests.Session` persistent connection pool (no subprocess spawning)
- In-memory response cache keyed by `sha256(system+prompt)` — deduplicates identical calls within a run
- One retry with 2s backoff on OpenRouter failure
- Claude CLI fallback

### Deleted: `analyzer.py`

270 lines of duplicated HTTP + retry + prompt logic consolidated into `llm_client.py` (transport) and `analyzer_v2.py` (prompt construction).

### Ranking algorithm changes

**Cross-source matching**: O(n²) nested loop replaced by O(n) hash-bucket grouping on `sha256(domain + path)`.

**Freshness-adjusted engagement**: raw score replaced by `score × (1/√(age_hours + 1))` — penalizes stale viral posts.

**Rebalanced weights**:

| Signal | Before | After |
|--------|--------|-------|
| Engagement (freshness-adjusted) | 40% | 30% |
| Recency | 15% | 15% |
| Cross-source | 15% | 20% |
| Content quality | 30% | 35% |

### Prompt engineering changes

New `extract_excerpt(content, max_chars=200)` in `schema.py` produces clean 200-char excerpts (strips HTML, collapses whitespace, truncates at sentence boundary).

Compact story block format replaces full content dumps:
```
[{id}] [{rank}/100] {title} | src:{source} | age:{h}h | score:{n} | quality:{q}/10
excerpt: "{200-char excerpt}"
```

Output schema moved to `system` message — sent once per call, not repeated per story.

### Estimated savings per run

| Area | Before | After | Savings |
|------|--------|-------|---------|
| Summarization prompt tokens | ~30,000 | ~9,000 | ~70% |
| Ranking prompt tokens (per story) | ~800 | ~120 | ~85% |
| Reddit fetch time | 24–48s | 6–12s | ~75% |
| Cross-source match ops | O(n²) 14,400 | O(n) 120 | ~99% |
| Est. cost per run | ~$0.20–0.25 | ~$0.07–0.12 | ~50–60% |
| Est. total pipeline time | 3–5 min | 1.5–3 min | ~40–50% |
