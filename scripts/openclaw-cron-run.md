# OpenClaw AI Digest cron runbook

Use this runbook for the OpenClaw cron jobs that run AI Digest at 8:00 AM and 5:00 PM Pacific.

## Intent

AI Digest remains independent, but scheduled production runs are owned by OpenClaw/Dexter instead of GitHub Actions. The 8 AM and 5 PM cron agent turns are pinned to `openrouter/free` when available so digest orchestration and any rich-summary repair prefer OpenRouter through OpenClaw routing, not direct AI Digest API keys.

## Required behavior

1. Work in `/Users/rickie/code/ai-digest-reader`.
2. Run with explicit OpenClaw mode:
   ```bash
   AI_DIGEST_ENGINE=openclaw \
   AI_DIGEST_OPENCLAW_STAGES=summary,notebooklm_ingest \
   AI_DIGEST_REQUIRE_SUMMARY=1 \
   AI_DIGEST_RANKER_PROVIDER=openclaw \
   RANKER_AI_ENABLED=1 \
   ./scripts/generate-and-deploy.sh
   ```
3. Ensure the final digest has a schema-v2 `summary` and passes:
   ```bash
   .venv/bin/python scripts/validate-digest.py ai-digest-reader/public/data/digest.json --require-summary
   ```
4. If the generated OpenClaw summary is too extractive/flat, Dexter may replace it with a richer schema-v2 summary generated from the ranked stories, but must obey these rules:
   - use only stories present in the digest
   - `mustRead[*].id` must match real story IDs
   - `mustRead[*].url` must match the source story URL
   - no invented sources, facts, or URLs
   - re-run `scripts/validate-digest.py --require-summary` after editing
   - rebuild before committing/pushing
5. Commit and push only after validation and frontend build pass.
6. Report to Rickie if anything fails: generation, validation, build, git push, or deploy-triggering commit.

## NotebookLM ingest behavior

Production runs must not spend project OpenRouter credits from the AI Digest app in OpenClaw mode. `generate-and-deploy.sh` defaults `AI_DIGEST_RANKER_PROVIDER=openclaw` and `RANKER_AI_ENABLED=1` when `AI_DIGEST_ENGINE=openclaw`, so semantic ranker quality scoring uses OpenClaw model routing and falls back to deterministic ranking if OpenClaw scoring fails. OpenRouter usage should come from the OpenClaw cron agent model (`openrouter/free`) or current OpenClaw routing, not from `llm_client.py` inside AI Digest.

Production runs use the robust NotebookLM path:

- cap: top 100 ranked digest sources
- direct URL import first
- automatic text fallback for URLs NotebookLM rejects
- duplicate/error placeholder pruning
- verification gate: 100/100 top sources covered, no extras, no duplicate URLs

For manual repair or rerun without regenerating/reranking the digest:

```bash
./scripts/notebooklm-ingest-latest.sh --cap 100 --account flyingbacon808
```

If a separate auth profile exists, prefer:

```bash
./scripts/notebooklm-ingest-latest.sh --cap 100 --notebooklm-home ~/.notebooklm-flyingbacon808
```

The script updates `output/<date>/digest.json` metrics and writes:

- `notebooklm-ingest.json`
- `notebooklm-top100-verification.json`

## Success report

A success report can stay brief. Include:

- run time
- engine mode
- summary status
- story count
- commit hash or "no changes"

## Failure report

Include:

- failed step
- log path
- concise error
- whether anything was committed/pushed
