# Hermes/OpenClaw 7-Day Summary Migration Benchmark Plan

## Goal

Migrate the AI digest summary engine from OpenClaw-only operation to a comparable Hermes-backed summary path using Omniroute’s `codex-combo` model, while measuring quality and performance for 7 days before deciding whether to switch defaults.

The primary objective is not just to "replace" OpenClaw, but to compare the two engines under the same inputs and schema constraints, with minimal coupling between the digest app and the summary runtime.

## What we are comparing

For each digest run over the next 7 days:

- OpenClaw summary output
- Hermes summary output using Omniroute `codex-combo`
- Output diffs
- Summary quality metrics
- Runtime and cost metrics
- Failure / fallback behavior

## Current context

- The digest pipeline currently generates summaries via the OpenClaw `digest-summary` CLI path.
- NotebookLM ingest is optional and should not block summary generation.
- The digest artifact is validated against a schema and grounded against ranked evidence.
- The frontend consumes `public/data/digest.json`.
- We already confirmed the digest pipeline can proceed even when NotebookLM is unavailable.

## Constraints

- Do not couple the digest app directly to Hermes internals.
- Keep the summary backend behind a thin adapter boundary.
- Preserve the existing schema and grounding checks.
- Measure before changing default behavior.
- Hermes should use Omniroute’s `codex-combo` model for the summary path.
- Keep OpenClaw as fallback during the benchmark window.

## Proposed approach

### Architecture

Add a summary-provider abstraction so the digest generator can call either backend:

- `openclaw` provider: current behavior
- `hermes` provider: new backend that invokes Hermes with Omniroute `codex-combo`

The digest app should only care about:

- input ranked evidence JSON
- provider selection via env/config
- output summary JSON
- validation results

### Benchmark strategy

For 7 days, run both providers on the same digest input when feasible, or run Hermes as primary while still recording OpenClaw in parallel on the same artifacts.

Recommended benchmark mode:

- generate the digest once
- call both summary providers on the same ranked-post payload
- store both outputs and metrics side by side
- choose one to publish for the frontend only after validation

## Files likely to change

### Core engine

- `engine/config.py`
  - add provider selection and Hermes model routing configuration
- `engine/openclaw.py`
  - keep OpenClaw adapter isolated
- `engine/hermes_summary.py` or similar new module
  - Hermes adapter for summary generation using Omniroute `codex-combo`
- `digest.py`
  - route summary generation through the new provider abstraction
  - emit benchmark artifacts for both providers
- `schema.py`
  - likely unchanged, but may need stricter validation helpers if comparison outputs differ

### Benchmark / reporting

- `scripts/generate-and-deploy.sh`
  - preserve phased execution
  - optionally add benchmark mode and artifact export
- `scripts/validate-digest.py`
  - ensure published digest still requires a valid generated summary
- new benchmark helper script under `scripts/` or `tools/`
  - compare outputs for 7 days
  - compute diffs and quality aggregates

### Data/artifacts

- `output/<date>/...`
  - store both provider outputs, metrics, and comparison results
- `ai-digest-reader/public/data/digest.json`
  - only publish the chosen summary path, not benchmark internals

### Documentation

- `README.md`
- `docs/technical-architecture.md`
- maybe a new `docs/summary-benchmark.md`

## Step-by-step plan

### Phase 1 — Define the adapter boundary

1. Inspect the existing summary-generation flow in `digest.py`.
2. Introduce a provider interface such as:
   - `generate_summary(provider, ranked_posts, config) -> (summary, meta)`
3. Keep OpenClaw as the first adapter implementation.
4. Add Hermes adapter config fields for:
   - provider name
   - model name (`codex-combo`)
   - command / invocation path
   - any required profile or routing flags

### Phase 2 — Implement Hermes summary backend

1. Identify the smallest Hermes invocation path that can produce a grounded JSON summary from ranked evidence.
2. Make the Hermes path file-based or stdin/stdout based.
3. Ensure the Hermes output conforms to the existing summary schema.
4. Keep Hermes isolated from the digest app by using a process boundary, not in-process imports.
5. Default Hermes model selection to Omniroute `codex-combo`.

### Phase 3 — Dual-run benchmark mode

1. Add a benchmark mode that runs both OpenClaw and Hermes against the same ranked evidence.
2. Store outputs separately:
   - `summary-openclaw.json`
   - `summary-hermes.json`
   - `summary-compare.json`
3. Produce a diff report showing:
   - schema validity
   - grounding differences
   - simple summary text diff
   - must-read item overlap
   - missing or extra citations

### Phase 4 — Define quality metrics

Track at least:

- schema pass/fail
- grounded must-read overlap
- reference correctness
- number of unique stories cited
- summary length
- user-facing coherence proxy
- error/fallback count
- manual preference score when reviewed

Suggested scoring rubric for manual review:

- 1 = unusable
- 2 = weak
- 3 = acceptable
- 4 = strong
- 5 = best-in-class

### Phase 5 — Define performance metrics

Track:

- end-to-end summary latency
- provider latency only
- p50 / p95 over 7 days
- token usage or proxy cost where available
- retry count
- failure count
- time to recover from a provider failure

### Phase 6 — Run the 7-day benchmark

1. Run daily digests for 7 days with both providers evaluated on the same input.
2. Save a daily comparison artifact.
3. Record which provider would have been chosen if quality + reliability are weighted.
4. Keep OpenClaw as fallback if Hermes fails.

### Phase 7 — Decide migration outcome

After 7 days, compare:

- average quality score
- grounding reliability
- average latency
- failure rate
- operational complexity
- cost

Decision outcomes:

- keep OpenClaw as default
- switch Hermes to default
- keep both with Hermes primary and OpenClaw fallback

## Verification plan

### Per-run checks

- `npm run check`
- `npm run build`
- digest validation on the chosen published summary
- comparison artifact exists for both providers
- summary schema passes for both outputs

### Benchmark verification

At the end of the 7-day window:

- verify that 7 comparison artifacts exist or note missing days
- compute aggregate quality and performance deltas
- inspect a few representative diffs manually
- confirm the chosen default is justified by the measured results

## Risks / tradeoffs

- Hermes may be better on quality but slower or more expensive.
- Omniroute routing may introduce a separate failure surface.
- Dual-running summaries increases cost during the benchmark window.
- A coupled implementation would make fallback and testing harder.
- If the Hermes adapter depends on live Hermes session state, it will be too sticky; keep it as a CLI/process boundary.

## Open questions

- What is the exact Hermes invocation path for `codex-combo` in this environment?
- Should both summaries be generated every day, or should OpenClaw be the fallback-only baseline after Hermes proves stable?
- Do we want the published digest to include benchmark metadata, or keep that in internal artifacts only?
- Should quality scoring be fully automatic, or include a short manual review each day?

## Success criteria

The migration is successful if, after 7 days:

- Hermes summaries are schema-valid and grounded
- Hermes quality is equal to or better than OpenClaw in most runs
- Hermes latency/cost is acceptable
- the app remains loosely coupled to the summary engine
- the decision to switch defaults is backed by measured data, not guesswork

## Immediate next steps

1. Confirm the exact Hermes/Omniroute command for `codex-combo` summary generation.
2. Add the provider abstraction.
3. Implement a dual-run benchmark mode.
4. Start collecting 7 days of comparison artifacts.
