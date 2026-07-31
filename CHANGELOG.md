# Changelog — AI Digest Pipeline

All notable changes to the digest pipeline (fetchers, scraper, ranker, summary
engine, orchestration). For frontend/reader changes see
[`ai-digest-reader/docs/CHANGELOG.md`](ai-digest-reader/docs/CHANGELOG.md).

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added — Phase 2: Ranking Signal (2026-07-31)

- **`ranker.py`** — `_title_quality_heuristic(post)`: scores a story 0-10 from
  title signals (known AI orgs/models, version numbers, news verbs) with
  penalties for meta/clickbait titles ("megathread", "day N of", "scrolling
  through"). Used as the quality fallback when a story has no scrapeable content
  and the LLM rater is unavailable or skipped it. This fixes the dead tie where
  every post collapsed to `content_quality = 0` (all posts tied at rank 5.5 in
  the 2026-07-31 run). Scraped posts keep the excerpt-length heuristic;
  LLM-rated posts keep their LLM score.

### Verified — Phase 2: Ranking Signal (2026-07-31)

- **`ranker.py`** — `_compute_cross_source_scores` was already source-agnostic:
  it buckets by canonical URL across all source prefixes (`rd`/`hn`/`rs`), so RSS
  stories already participate in cross-source corroboration. The plan assumed RSS
  was excluded; it was not. Added a regression test to lock the behavior in. No
  production code change.

### Added — Phase 1: Data Acquisition (2026-07-31)

Part of the quality-enhancement plan
(`.hermes/plans/2026-07-31_153500-ai-digest-quality-enhancement.md`).

- **`scraper.py`** — `_extract_with_defuddle(url)`: new primary article extractor
  that shells out to the `defuddle` CLI (`defuddle parse <url> --md`). It handles
  its own fetch + extraction and copes with JS-heavy pages better than the
  requests+trafilatura chain. Runs first in `_fetch_and_extract`; on any failure
  (missing binary, timeout, non-zero exit, short output) the existing
  trafilatura → readability → lxml → metadata → jina → archive chain is unchanged.
  Configurable via `DEFUDDLE_BIN` and `SCRAPER_DEFUDDLE_TIMEOUT` (default 12s).
- **`fetchers/reddit.py`** — Reddit now recovers via the Atom RSS feed
  (`hot.rss`) when the JSON API returns a terminal 401/403/429. Reddit's JSON
  endpoints are permanently blocked for unauthenticated clients, but RSS stays
  available and returns fresh posts. Verified live: r/LocalLLaMA returns current
  stories (e.g. DeepSeek V4 Flash) instead of empty/stale-cache results.
- **`fetchers/hn.py`** — `fetch_hn_top_comments(story_id, limit)`: pulls the full
  comment tree from the Algolia `items` endpoint in a single request and flattens
  it breadth-first to a shallow depth (top-level comment + immediate reply).
  Exported from the `fetchers` package.
- **`digest.py`** — attaches the top 5 comments as `discussion_context` to the
  top-N HN stories so the summarizer sees community signal, not just titles.
  Controlled by `AI_DIGEST_HN_COMMENT_STORIES` (default 10; set 0 to disable).
  Runs only on AI-enabled runs (`--no-ai` skips enrichment).

### Changed — Phase 1: Data Acquisition (2026-07-31)

- **`scraper.py`** — replaced the `import os as _os` / `del _os` workaround with a
  real top-level `import os` and added `import subprocess` (needed by defuddle).
- **`fetchers/reddit.py`** — `REDDIT_RSS_FALLBACK_ON_TERMINAL` default flipped
  `False` → `True` (RSS recovery on terminal JSON status is now the default).
- **`fetchers/reddit.py`** — `REDDIT_GLOBAL_BLOCK_PROBE` default flipped
  `True` → `False`. The global probe short-circuited *all* subreddit fetches on a
  single 403, which prevented the new per-subreddit RSS recovery from running.
  Re-enable it only if you also set `REDDIT_RSS_FALLBACK_ON_TERMINAL=0` and rely
  purely on the local cache.
- **`fetchers/hn.py`** — `strip_html()` now also unescapes HTML entities
  (`&gt;`, `&#x2F;`, `&amp;`, …) so comment text fed to the summarizer is clean.

### Notes / Known Limitations

- **RSS posts lack engagement metadata.** The Reddit RSS feed provides titles and
  URLs but not `score`, `num_comments`, or `created_utc` — those arrive as
  `0` / `None`. Ranking therefore leans on title heuristics and cross-source
  signals for Reddit (see Phase 2). A proper long-term fix is a registered Reddit
  OAuth app (manual step at reddit.com/prefs/apps), not yet implemented.
- **pullpush.io evaluated and rejected.** Considered as an archive fallback for
  blocked Reddit, but its index is stale (latest data ~May 2025; zero posts in the
  last week), so it would inject outdated stories. Not used.

### Tests

- `tests/test_scraper.py` — +7 tests for the defuddle extractor (success, non-zero
  exit, missing binary, timeout, short-output rejection, preferred-ordering, and
  fallback-to-trafilatura). 15 passing.
- `tests/test_reddit.py` — updated for new defaults: 403→RSS fallback by default,
  403→empty when fallback disabled, probe disabled by default. 8 passing.
- `tests/test_hn.py` — new: 8 tests for `fetch_hn_top_comments` (flattening, limit,
  shallow replies, HTTP/network error handling, truncation) and `strip_html`
  (tag removal + entity unescaping).
- Full suite: **171 passing**.

---

## [Prior work]

See git history and `docs/superpowers/` for earlier changes, including:

- **2026-04-22** — Quality-first overhaul: O(n) cross-source matching,
  freshness-adjusted engagement scoring, rebalanced signal weights, compact
  prompt engineering (`docs/superpowers/specs/2026-04-22-quality-first-overhaul-design.md`).
- **2026-04-15** — Aggressive perf/security/efficiency refactor
  (`docs/superpowers/plans/2026-04-15-aggressive-perf-security-efficiency.md`).
- **2026-04-15** — Strict v2 summary schema, AI summary feature
  (`ai-digest-reader/docs/CHANGELOG.md`).
