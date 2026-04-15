# Technical Architecture

## Data Flow

1. `digest.py` orchestrates Reddit and HN fetchers, normalizes payloads, and writes `output/<date>/digest.json`.
2. `ai-digest-reader/public/data/digest.json` is consumed by the Astro frontend.
3. Frontend state merges Reddit and HN stories and applies ranked ordering for the `all` source view.

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

## Story Schema (v2)

Each story uses compact keys:

- `i`: stable id (`rd-<index>` or `hn-<index>`)
- `t`: title
- `u`: external/original article URL
- `p`: discussion permalink (Reddit thread or HN item URL)
- `b`: optional body excerpt (plain text)
- `s`: score/upvotes
- `c`: comment count
- `a`: author

## Link Routing Rules

- Primary card/title click navigates to `p || u` in the same tab.
- Secondary external link uses `u` in the same tab when `u !== p`.
- This preserves swipe-back behavior on mobile browsers.

## Ranking Strategy (`all` feed)

- Stories are grouped by source prefix (`rd`, `hn`, extensible for future sources).
- Score and comment signals are min-max normalized per source.
- Dynamic weights adapt to available signals:
  - score + comments present: `0.4 + 0.3` (+ recency baseline `0.3`)
  - only score: `0.7`
  - only comments: `0.7`
  - no engagement signals: recency only
- Current recency is neutral (`0.5`) until per-story timestamps are added.

## Mobile UX Decisions

- Card and list interactions avoid `target="_blank"`.
- Touch targets are increased for better tap accuracy.
- List view switches to stacked cards on narrow screens to eliminate horizontal scrolling.
- Optional body excerpts improve skimmability without AI-generated copy.
