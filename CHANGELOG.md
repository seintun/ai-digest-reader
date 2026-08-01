# Changelog — AI Digest Pipeline

All notable changes to the digest pipeline (fetchers, scraper, ranker, summary
engine, orchestration). For frontend/reader changes see
[`ai-digest-reader/docs/CHANGELOG.md`](ai-digest-reader/docs/CHANGELOG.md).

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed — Production Correctness (2026-07-31)

- **`config.py`** — removed the dead Reuters Tech RSS feed (`feeds.reuters.com`
  no longer resolves; it threw a DNS error on every run). 14 → 13 feeds.
- **`digest.py` / `scripts/quality_gate.py`** — split the misleading single
  "evidence coverage" metric into two honest signals: `content_coverage_pct`
  (informational; structurally low because most RSS/Reddit items aren't scrape
  candidates) and `scrape_success_rate` (the actionable extraction-health
  signal, cache-inclusive). The quality gate now thresholds on
  `scrape_success_rate` (default 50%) and only when there were scrape
  candidates, so it no longer warns on every run — and a fully-cached run
  correctly reports 100% instead of a false 0%.
- **`scripts/write_summary_benchmark_report.py`** — in normal single-provider
  runs the benchmark block is empty, which made the report claim "both providers
  failed" even when the summary succeeded. It now reports the real summary
  outcome; the provider-comparison view only renders in actual benchmark mode.
- **Cron job (AI Digest)** — enabled `AI_DIGEST_ANALYSIS_ENABLED=1` so the
  stage-3 analysis actually runs in production; the Discord report now posts the
  TL;DR + breaking + top-3 mustRead links + analysis (when present) + any
  quality-gate warnings, instead of a terse success/failure line.

### Added — Phase 4: Delivery & Reader UX (2026-07-31)

- **`ai-digest-reader/src/types.ts`** — new `DigestAnalysis` interface; `analysis?`
  added to `DigestSummary`.
- **`ai-digest-reader/src/pages/index.astro`** — the summary card now renders a
  collapsible "Analysis & Implications" block (native `<details>`, no carousel/JS
  changes) when the summary carries an `analysis` object: implications list,
  skeptic's take, evidence basis, and a color-coded confidence badge.

### Added — Phase 5: Operational Hardening (2026-07-31)

- **`digest.py`** — new `metrics.quality` block: `total_stories`,
  `stories_with_content`, `evidence_coverage_pct`, `source_counts`
  (reddit/hackernews/rss), and `analysis_generated`. Evidence coverage is printed
  to the console. (This surfaced a real signal: a typical run has ~6% evidence
  coverage because Reddit self-posts and zero-score RSS items aren't scrape
  candidates — only HN external links are.)
- **`scripts/quality_gate.py`** (new) — soft quality-regression gate. Warns when
  evidence coverage drops below a threshold (default 30%) or the summary is
  missing/invalid for N consecutive runs (default 2, tracked in a state file).
  Never blocks the pipeline; exits 2 on warnings.
- **`scripts/hermes-digest-run.sh`** — runs the quality gate after a successful
  run and folds warnings into the report JSON so the cron agent can surface them
  to Discord.

### Added — Phase 3: Multi-Stage Summarization (2026-07-31)

- **`engine/analysis.py`** (new) — stage-3 analysis pipeline. Runs one extra LLM
  call after the base schema-v2 summary and attaches an `analysis` block:
  `implications` (engineers/industry), `skeptic_take` (strongest counter-argument),
  `confidence` (high/medium/low), and `evidence_basis` (verified vs title-only).
  Reuses the Hermes CLI plumbing from `engine.summary` and the robust
  `parse_llm_json` scanner, which tolerates the CLI's warning line + reasoning-box
  preamble before the JSON. Gated by `AI_DIGEST_ANALYSIS_ENABLED=1` (default off).
  Verified end-to-end against the live Hermes CLI.
- **`analyzer_v2.py`** — summary prompt now tags each story
  `evidence:verified-content` vs `evidence:title-only` and instructs the model not
  to invent specifics/numbers/quotes for title-only stories (and to prefer
  verified-content stories for mustRead/breaking).
- **`engine/config.py`** — `summary_excerpt_chars` default bumped 120 → 400 for
  richer grounding; new `analysis_enabled` flag (`AI_DIGEST_ANALYSIS_ENABLED`).
- **`digest.py`** — wires the analysis stage after the summary, adds
  `analysis_seconds` to runtime metrics and an `analysis` entry to summary metrics.

### Added — Extraction-Stage Telemetry (2026-07-31)

- **`scraper.py`** — `_fetch_and_extract` now returns `(content, error, telemetry)`
  recording the winning extractor, the ordered list of stages attempted, and a
  `stage -> reason` map of every fallthrough (defuddle → fetch → trafilatura →
  readability → lxml → metadata → jina → archive). `scrape_articles_with_stats`
  aggregates this into an `extractor_breakdown`: per-extractor win counts, a
  `none` count, and a `failure_reasons` sub-map counting `stage:reason` pairs
  (e.g. `defuddle:no_output`, `fetch:http_403`).
- **`digest.py`** — surfaces the breakdown in `metrics.scraping.extractor_breakdown`
  and prints `extractor wins:` / `extraction fallthroughs:` lines to the console.
  Answers "how many sites fell through defuddle to the next stage, and why".

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
- Full suite: **194 passing**.

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
