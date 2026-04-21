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
