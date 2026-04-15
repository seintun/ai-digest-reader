# Technical Architecture

## Data Flow

1. `digest.py` orchestrates Reddit and HN fetchers, normalizes payloads, and writes `output/<date>/digest.json`.
2. `ai-digest-reader/public/data/digest.json` is consumed by the Astro frontend.
3. Frontend state merges Reddit and HN stories and applies ranked ordering for the `all` source view.

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
