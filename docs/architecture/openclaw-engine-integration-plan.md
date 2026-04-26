# OpenClaw Engine Integration Plan

## Goal

Keep AI Digest Reader independent while allowing it to explicitly switch into an OpenClaw-powered engine mode for expensive AI work and, later, shared research pipeline execution.

AI Digest must continue to work as a standalone product with its own repository, reader UI, schema, deploy script, and fallback behavior. OpenClaw should be an optional backend, not a hidden dependency.

## Non-negotiables

1. **Independence first**
   - AI Digest must still run without OpenClaw.
   - The current `digest.json` contract and Astro frontend should remain stable.

2. **Explicit engine selection**
   - No silent use of OpenClaw, parent-shell credentials, or unrelated project environment variables.
   - OpenClaw mode must require an explicit setting such as `AI_DIGEST_ENGINE=openclaw`.

3. **Credential consent boundary**
   - If a run would use OpenClaw-managed model credentials, the script/assistant must make that explicit.
   - If the required project-local key is missing in standalone mode, fail clearly or run in no-AI mode according to config; do not borrow credentials silently.

4. **Schema stability**
   - The frontend consumes `ai-digest-reader/public/data/digest.json`.
   - Any OpenClaw response must be adapted into the existing AI Digest schema before deploy.

5. **Low hallucination risk**
   - Deterministic ranking and evidence fields remain primary.
   - LLM summaries must cite/point to actual story IDs from the input.
   - Validation gates must reject summaries that reference missing stories or URLs.

6. **Cache isolation**
   - Digest runs must use a digest profile/cache namespace.
   - No cache/ranking contamination between AI Digest, general OpenClaw research, YouTube research, or NotebookLM workflows.

## Target architecture

```text
AI Digest Reader repo
  ├─ collection/scraping layer
  │   ├─ Reddit
  │   ├─ Hacker News
  │   └─ RSS
  │
  ├─ engine adapter layer
  │   ├─ standalone engine
  │   │   ├─ local ranker.py
  │   │   └─ local analyzer_v2.py / OpenRouter if explicitly configured
  │   │
  │   └─ openclaw engine
  │       ├─ OpenClaw local command/API client
  │       ├─ research_engine digest profile
  │       └─ OpenClaw model routing / tools, explicitly selected
  │
  ├─ schema adapter / validator
  │   └─ emits current digest.json v4 shape
  │
  └─ deployment layer
      ├─ build Astro frontend
      └─ commit/push to trigger Vercel
```

OpenClaw side:

```text
OpenClaw research-engine
  ├─ profile: digest
  ├─ cache namespace: digest + version + inputs
  ├─ digest_adapter.py
  ├─ optional LLM quality scoring
  ├─ summary generation service/command
  └─ metrics + audit output
```

## Engine modes

### `AI_DIGEST_ENGINE=standalone`

Default mode.

Uses AI Digest's existing local pipeline:

- `digest.py`
- `fetchers/`
- `scraper.py`
- `ranker.py`
- `analyzer_v2.py`
- direct OpenRouter only if `OPENROUTER_API_KEY` is explicitly project-configured or explicitly approved for the run

Recommended standalone failure policy:

```bash
AI_DIGEST_STANDALONE_AI=required|optional|off
```

- `required`: fail if project-local LLM credentials are absent
- `optional`: publish digest without AI summary if LLM unavailable
- `off`: deterministic-only digest, no summary/reranking LLM calls

### `AI_DIGEST_ENGINE=openclaw`

Opt-in mode.

Uses AI Digest for collection/deploy initially, but delegates selected AI stages to OpenClaw.

Recommended config:

```bash
AI_DIGEST_ENGINE=openclaw
AI_DIGEST_OPENCLAW_MODE=cli        # cli first; http later if needed
AI_DIGEST_OPENCLAW_PROFILE=digest
AI_DIGEST_OPENCLAW_STAGES=summary  # later: summary,llm_quality,rank
AI_DIGEST_OPENCLAW_REQUIRE_CONFIRM=false # true for manual interactive runs if desired
```

OpenClaw mode should not read `OPENROUTER_API_KEY` from AI Digest. It should use OpenClaw's configured model routing only because the user explicitly selected OpenClaw mode.

## Recommended implementation phases

### Phase 0 — Contract and safety rails

Deliverables:

- Add this document.
- Add/update environment docs for engine selection and credential rules.
- Add a run preflight that prints:
  - selected engine
  - selected AI stages
  - credential source category, never the secret value
  - fallback policy
  - output path

Tests:

- Preflight reports standalone with blank `.env` as no project-local key.
- Preflight reports OpenClaw mode only when `AI_DIGEST_ENGINE=openclaw` is set.
- Blank `.env` values do not override nonblank values accidentally.

Acceptance:

- A run log makes it obvious whether OpenClaw or standalone engine was used.

### Phase 1 — Engine interface inside AI Digest

Create a small internal interface, not a full rewrite.

Proposed files:

```text
engine/
  __init__.py
  base.py
  standalone.py
  openclaw.py
  validation.py
```

Interface sketch:

```python
class DigestEngine(Protocol):
    name: str

    def rank(self, posts: list[dict], *, context: DigestRunContext) -> EngineRankResult:
        ...

    def summarize(self, ranked_posts: list[dict], *, context: DigestRunContext) -> EngineSummaryResult:
        ...
```

Initial behavior:

- `StandaloneEngine` wraps existing `ranker.py` and `analyzer_v2.py`.
- `OpenClawEngine` can initially support only `summarize()`.
- Unsupported OpenClaw stages fall back only if policy explicitly allows it.

Tests:

- Engine selection from env.
- Standalone remains default.
- OpenClaw mode with unsupported stage fails clearly unless fallback is enabled.

Acceptance:

- Existing digest output is unchanged in standalone mode.

### Phase 2 — OpenClaw summary delegation

Start with only the AI summary. This is the lowest-risk expensive AI stage.

Flow:

```text
digest.py collects/scrapes/ranks locally
  → writes ranked candidate payload to temp file
  → OpenClawEngine calls research-engine digest summary command
  → validates returned summary
  → inserts summary into digest.json
```

Potential command shape:

```bash
python -m research_engine.cli digest-summary \
  --profile digest \
  --input /tmp/ai-digest-ranked-posts.json \
  --output /tmp/ai-digest-summary.json \
  --metrics-json output/YYYY-MM-DD/openclaw-summary-metrics.json
```

If OpenClaw does not yet have this command, add it in `projects/research-engine` as a thin CLI wrapper over `research_engine.digest_adapter` / summary service.

Validation gates:

- summary exists
- `schema_version == "2"`
- exactly 3 themes
- exactly 3 `mustRead` items
- `mustRead[*].id` exists in ranked posts
- `mustRead[*].url` matches or is derived from the matching story
- `fullBrief.sections` has 2-4 items

Tests:

- Mock OpenClaw command success.
- Mock malformed summary rejected.
- Mock timeout/failure follows configured fallback policy.

Acceptance:

- `AI_DIGEST_ENGINE=openclaw AI_DIGEST_OPENCLAW_STAGES=summary ./scripts/generate-and-deploy.sh` produces a digest with a validated summary and metrics showing OpenClaw as source.

### Phase 3 — OpenClaw LLM quality scoring / reranking

After summary mode is stable, optionally delegate LLM quality scoring.

Flow:

```text
posts + excerpts
  → OpenClaw digest profile scorer
  → returns quality scores and per-item rationale/metadata
  → local deterministic ranker incorporates scores
```

Guardrails:

- Deterministic rank remains primary.
- LLM score is bounded and optional.
- If LLM scoring fails, fall back to deterministic ranking.
- Store scoring metadata in metrics, not as UI-facing truth.

Tests:

- Quality scores only affect configured weight.
- Missing scores do not crash ranking.
- Digest and research-engine cache keys include profile + stage + version.

Acceptance:

- Side-by-side run shows similar or better top-story quality without schema drift.

### Phase 4 — Full research-engine adapter mode

Only after phase 2/3 confidence.

In this mode, AI Digest can send normalized raw sources to OpenClaw `research_engine.digest_adapter.run_digest_workflow(...)` and receive a complete digest-shaped payload.

This should remain optional because AI Digest's current production pipeline is already specialized and hardened.

Acceptance:

- A/B output comparison between local pipeline and full OpenClaw adapter.
- No deploy until output passes validation and diff review.

### Phase 5 — Telegram and cron operation

Add a safe operational wrapper:

```bash
scripts/run-digest.sh --engine openclaw --deploy
scripts/run-digest.sh --engine standalone --no-deploy
scripts/run-digest.sh --engine openclaw --preview
```

Telegram Dexter command behavior:

1. Confirm engine if it would use OpenClaw-managed credentials and the setting is not already explicit.
2. Run preflight.
3. Generate digest.
4. Validate `digest.json`.
5. Build frontend.
6. Commit/push only if validation passes.
7. Report summary:
   - engine
   - model/provider if available
   - story count
   - summary status
   - cost/usage if available
   - commit hash / deploy status

Cron behavior:

- Cron must use explicit config file or env file, not inherited interactive shell state.
- Cron should fail clearly if engine config is ambiguous.
- Cron should write logs under `output/YYYY-MM-DD/` and/or `logs/`.

## Fallback policy matrix

| Failure | Standalone default | OpenClaw default | Notes |
|---|---|---|---|
| No project-local OpenRouter key | no-AI or fail based on `AI_DIGEST_STANDALONE_AI` | not relevant | Do not borrow OpenClaw key silently |
| OpenClaw unavailable | not relevant | fail before deploy | Optional fallback only if explicitly configured |
| OpenClaw summary malformed | use no summary or fail based on policy | fail before deploy recommended | Prevent hallucinated/invalid UI data |
| LLM quality scoring fails | deterministic rank | deterministic rank | Safe fallback |
| Build fails | no commit/push | no commit/push | Keep deploy atomic-ish |
| Git remote changed | stash/rebase or fail with clear instructions | same | Avoid partial deploy confusion |

Recommended default for production OpenClaw mode:

```bash
AI_DIGEST_OPENCLAW_ON_FAILURE=fail-no-deploy
```

## Deploy safety improvements

Current script does generation, copy, build, commit, and push in one flow. Improve it with staged outputs:

```text
output/YYYY-MM-DD/digest.candidate.json
  → validate
  → copy to ai-digest-reader/public/data/digest.json
  → build
  → commit/push
```

Add validation before copy and before commit:

- JSON parse succeeds
- schema version present
- story arrays non-empty
- `summary` required/optional according to policy
- if summary exists, `validate_summary(summary)` passes
- metrics record engine and credential source category

## Metrics and audit fields

Add or preserve these fields in `metrics.json` and/or digest metrics:

```json
{
  "engine": {
    "name": "standalone|openclaw",
    "profile": "digest",
    "stages": ["summary"],
    "credential_source": "project_env|openclaw_explicit|none",
    "fallback_policy": "fail-no-deploy"
  }
}
```

Never log secret values.

## Documentation updates required

AI Digest Reader:

- `docs/technical-architecture.md`
  - describe engine adapter layer and OpenClaw optional mode
- `docs/architecture/automation.md`
  - document Telegram/cron behavior and explicit engine env
- `.env.example`
  - add engine selection variables with safe comments
- `README.md`
  - quick usage examples
- `docs/TROUBLESHOOTING.md`
  - missing summary, OpenClaw unavailable, credential-source mismatch

OpenClaw research-engine:

- `docs/architecture.md`
  - describe AI Digest as optional product/profile consumer
- `docs/technical.md`
  - document digest profile, adapter command/API contract, cache isolation
- `README.md`
  - add digest adapter examples and warning that AI Digest is not automatically dependent on research-engine

## Open questions before implementation

1. Should OpenClaw mode fail the deploy if summary generation fails, or deploy without summary?
   - Recommendation: fail-no-deploy for OpenClaw mode, optional no-summary for standalone mode.

2. Should Telegram-triggered runs require confirmation every time OpenClaw credentials are used?
   - Recommendation: if `AI_DIGEST_ENGINE=openclaw` is explicit in project config, no repeated confirmation; if inferred/ad hoc, ask.

3. Should cron use OpenClaw mode by default?
   - Recommendation: not until phase 2 has several successful manual runs.

4. Should we expose OpenClaw via HTTP or CLI first?
   - Recommendation: CLI first. Less surface area, easier auth story, fewer security risks.

## Definition of done

- AI Digest standalone mode still passes all tests and produces the same schema.
- OpenClaw summary mode works with explicit config and no direct OpenRouter key in AI Digest.
- Every run records engine, stages, and credential source category.
- Summary validation prevents missing/invalid/hallucinated references from deploying.
- Telegram and cron wrappers run the same validated path.
- Docs in both repos explain the architecture, config, fallback behavior, and troubleshooting path.
