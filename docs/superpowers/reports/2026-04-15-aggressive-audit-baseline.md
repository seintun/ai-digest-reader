# Aggressive Audit Baseline (2026-04-15)

## Baseline Verification

### Python

- Command: `.venv/bin/python -m pytest`
- Result: `78 passed in 2.71s`

### Frontend

- Command: `npm run check`
- Result: pass (`0 errors`, `2 hints`)
- Hints:
  - unused import in `src/pages/index.astro`
  - unused `getDomain` in `src/pages/index.astro`

- Command: `npm run build`
- Result: pass
- Key output:
  - built in `505ms`
  - main hoisted js: `34.01 kB (gzip 7.32 kB)`

## Ranked Findings Matrix

| Finding | Domain | Severity | ROI | Target Metric | Candidate Files | Owner Agent |
|---|---|---|---|---|---|---|
| Unsanitized `innerHTML` rendering of untrusted story fields (XSS risk) | frontend/security | P0 | very high | eliminate script injection vector | `ai-digest-reader/src/pages/index.astro` | devils-advocate |
| Untrusted URL injection in anchors/window redirects | frontend/security | P0 | high | enforce http/https-only urls | `ai-digest-reader/src/pages/index.astro` | devils-advocate |
| `schema.py` uses `assert` for validation | pipeline/security | P0 | high | deterministic validation under optimized runtime | `schema.py` | pipeline-profiler |
| Tests use brittle hardcoded `sys.path.insert(...)` | quality/correctness | P0 | high | portable, reliable tests | `tests/test_*.py` | pipeline-profiler |
| Triple render per update (cards/list/glance all rebuilt) | frontend/perf | P1 | high | reduce render/DOM churn | `ai-digest-reader/src/pages/index.astro` | frontend-profiler |
| Repeated inline SVG and string-heavy template generation | frontend/perf | P1 | medium-high | reduce parse/GC overhead | `ai-digest-reader/src/pages/index.astro` | frontend-profiler |
| HN fetch is sequential N+1 requests | pipeline/perf | P1 | high | reduce fetch latency | `fetchers/hn.py` | pipeline-profiler |
| Reddit fetch mapping duplication and broad exception swallowing | pipeline/maintainability | P1 | medium | simplify and improve reliability | `fetchers/reddit.py` | pipeline-profiler |
| Incorrect HN markdown link format | correctness | P1 | medium | valid output links | `formatter.py` | pipeline-profiler |
| Potentially duplicate control/view init listeners | frontend/perf | P1 | medium | reduce redundant handlers | `ai-digest-reader/src/components/Controls.astro`, `ai-digest-reader/src/components/ViewSwitcher.astro` | frontend-profiler |
| Service worker cache policy too broad + missing offline asset | frontend/reliability | P2 | medium | avoid stale/poisoned cache hazards | `ai-digest-reader/public/sw.js` | devils-advocate |
| Duplicate generation paths may drift schema/contracts | architecture | P2 | medium | single source of truth for data contracts | `digest.py`, `ai-digest-reader/scripts/generate_json.py` | devils-advocate |

## Phase Priorities

1. **P0:** security/correctness blockers (XSS/url safety, schema validation robustness, test reliability)
2. **P1:** runtime/perf wins (render churn, fetch efficiency, formatter correctness)
3. **P2:** structural cleanup and broader architecture risks

## Subagent Evidence IDs

- Frontend audit: `ses_26cd8cb51ffecrF0INxJ58xu0w`
- Pipeline audit: `ses_26cd73814ffeE6C4RDUIZUW7TJ`
- Security devil's advocate: `ses_26cd63c12ffe2FVzSyJ1MpndOr`

## Applied Changes and Deltas

### Verification Matrix (post-refactor)

- Python tests: `.venv/bin/python -m pytest` -> `79 passed`
- Frontend checks: `npm run check` -> pass (`0 errors`, `0 warnings`, `0 hints`)
- Frontend build: `npm run build` -> pass (static build completed)

### Runtime and Build Deltas

- Python test runtime baseline -> latest: `2.71s` -> `~1.39-1.93s` across post-change runs.
- Frontend build baseline -> latest: `~505ms` -> `~492-521ms` (within noise range).
- Main client artifact baseline -> latest: `34.01 kB (gzip 7.32 kB)` -> `34.67 kB (gzip 7.51 kB)`.

### Security Delta

- Closed: untrusted story text now escaped before insertion.
- Closed: external links are protocol-allowlisted (`http`/`https`).
- Closed: schema validation no longer relies on `assert` semantics.

### Efficiency/Compactness Delta

- Frontend now renders only active view per state update (cards/list/glance).
- Removed duplicate/unused frontend modules and stale types:
  - deleted 7 unused source files (`components` + `lib`)
  - removed unused interfaces in `src/types.ts`
- HN fetcher uses bounded parallel fetches for item requests.
- Reddit fetch normalization consolidated into helper functions.
- HN markdown output link formatting corrected.
