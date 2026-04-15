# Body Text + Comment Links Design

**Date:** 2026-04-15  
**Status:** Approved

## Problem

Story cards currently only show the title, author, score, and comment count. Two things are missing:

1. **Body text** — Reddit self-posts and HN text posts include content in the `b` field, but it's clamped too aggressively (1–2 lines) to be readable.
2. **Comment links** — The comment count is a static `<span>`. Clicking it does nothing, but users want to jump directly to the HN or Reddit discussion thread.

## Goal

Normalize the reading experience across HN and Reddit:
- Surface post body text (first 3 lines) when available
- Make comment counts clickable, redirecting to the source discussion
- No new API calls, no backend changes, no schema changes — all data is already fetched

## Data Available (no changes needed)

All fields already exist in the v2 story schema:

| Field | Content |
|-------|---------|
| `b` | Body/selftext (first 280 chars, HTML-stripped). Present for Reddit self-posts and HN text posts. |
| `p` | Discussion permalink — `https://news.ycombinator.com/item?id={id}` for HN, `https://reddit.com/r/…` for Reddit |
| `u` | External article URL (may equal `p` for self-posts with no external link) |
| `c` | Comment count |

## Changes

Frontend only. Three files touched, same pattern applied consistently.

### StoryCard.astro (grid/card view)

1. `line-clamp-2` → `line-clamp-3` on the body `<p>` (line 63)
2. Wrap comment count `<span>` in `<a href={discussionUrl} target="_blank" rel="noopener noreferrer">` (lines 83–88)

### StoryList.astro (list view — mobile card + desktop table)

1. Mobile card body: `line-clamp-1` → `line-clamp-3` (line 63)
2. Mobile card comment count: wrap `c {formatComments(story.c)}` in `<a href={discussionUrl} target="_blank">`  (line 77)
3. Table body: `line-clamp-1` → `line-clamp-2` (line 118)
4. Table comment count cell: wrap count in `<a href={discussionUrl} target="_blank">` (lines 136–138)

### StoryGlance.astro (pill view)

No changes — intentionally minimal.

## Resulting Card Layout

```
[src icon] Story title here, possibly long enough
           to wrap to a second or third line
Body text shows up to three lines when present,
truncated with ellipsis after that...

[author]  ↑ score  [💬 345] ← links to HN/Reddit thread
                       [domain.com ↗] ← external article
```

The comment link and external pill are both present when applicable, absent when not (e.g. a Reddit self-post with no external URL won't show a pill).

## Verification

1. Run `npm run dev` in `ai-digest-reader/`
2. Check a Reddit self-post card — body text should show 3 lines
3. Check an HN text post — body text should show
4. Click the comment count on any card — should open `news.ycombinator.com/item?id=…` or Reddit thread in new tab
5. Check a link post (HN or Reddit with external URL) — external pill should still appear alongside comment link
6. Verify list view and mobile card view match card view behavior
