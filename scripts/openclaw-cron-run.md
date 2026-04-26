# OpenClaw AI Digest cron runbook

Use this runbook for the OpenClaw cron jobs that run AI Digest at 8:00 AM and 5:00 PM Pacific.

## Intent

AI Digest remains independent, but scheduled production runs are owned by OpenClaw/Dexter instead of GitHub Actions. OpenClaw may use its configured primary/fallback model routing for the rich summary because Rickie explicitly requested this mode.

## Required behavior

1. Work in `/Users/rickie/code/ai-digest-reader`.
2. Run with explicit OpenClaw mode:
   ```bash
   AI_DIGEST_ENGINE=openclaw \
   AI_DIGEST_OPENCLAW_STAGES=summary \
   AI_DIGEST_REQUIRE_SUMMARY=1 \
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
