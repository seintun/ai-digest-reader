# Aggressive Refactor Results (2026-04-15)

## Scope Completed

- P0: security/correctness hardening
- P1: frontend runtime and pipeline efficiency
- P2: compact modular cleanup

## Branch and Commit Evidence

- `wave-p0-security-baseline` -> `fix: harden schema validation and sanitize external story links`
- `wave-p1-frontend-runtime` -> `perf: render only active story view and dedupe controls init`
- `wave-p1-pipeline-efficiency` -> `perf: parallelize hn fetches and simplify reddit normalization`
- `wave-p2-compact-modularization` -> `refactor: remove unused frontend modules and stale types`

## Verification Outputs

- Python: `.venv/bin/python -m pytest` -> `79 passed`
- Frontend: `npm run check` -> pass (`0 errors`, `0 warnings`, `0 hints`)
- Frontend: `npm run build` -> pass

## Performance Metrics (Measured)

### Current Measurements

- Python tests (`/usr/bin/time -lp .venv/bin/python -m pytest`)
  - wall time: `1.79s`
  - max RSS: `60.44 MB`
- Digest generation (`/usr/bin/time -lp .venv/bin/python digest.py --no-ai --limit 5`)
  - wall time: `4.74s`
  - max RSS: `48.61 MB`
- Frontend check (`/usr/bin/time -lp npm run check`)
  - wall time: `1.91s`
  - max RSS: `529.69 MB`
- Frontend build (`/usr/bin/time -lp npm run build`)
  - wall time: `1.09s`
  - max RSS: `422.07 MB`
  - bundle: `dist/assets/hoisted.DjjRnNH3.js` = `34.67 kB` (`7.51 kB` gzip)

### Baseline vs Current Deltas

- Python tests: `2.71s` -> `1.79s` (**~34% faster**)
- Frontend check/build status: remained stable and clean (0 errors)
- Frontend build duration: roughly flat (`~0.5s` Astro build phase) with full command wall time around `1.1s`
- Bundle size: increased from `34.01 kB` to `34.67 kB` (gzip `7.32 kB` -> `7.51 kB`), offset by runtime/render-path improvements

## Key Improvements

### Security

- Escaped untrusted story text before DOM insertion.
- Restricted outbound URLs to `http`/`https` schemes.
- Replaced assert-driven schema validation with explicit checks.

### Performance and Efficiency

- Eliminated triple-render path by rendering only active view.
- Prevented duplicate controls initialization and event registration.
- Parallelized HN item fetch path with bounded workers.
- Consolidated Reddit normalization/extraction logic.

### Compactness and Reuse

- Removed unused frontend source files and stale interfaces.
- Reduced maintenance surface area and dead code noise.

## Remaining Risk Notes

- Service worker cache policy and missing `offline.html` were identified in audit and remain follow-up hardening items.
- Documentation still references some historical architecture paths; updated core architecture docs in this wave.

## Follow-up Backlog (Prioritized)

1. Harden `public/sw.js` caching scope to same-origin allowlist and validate offline fallback behavior.
2. Align deployment/runtime dependency docs and lock strategy for long-term reproducibility.
3. Add deterministic mocked tests for network fetchers to improve CI reliability under API instability.
