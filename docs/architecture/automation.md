# Automation & CI/CD Architecture

## Overview
DailyDigest can be run manually or automatically via GitHub Actions or system cron.

## Deployment Modes

### 1. Manual (developer)
```bash
./scripts/setup.sh           # First time only
./scripts/generate-and-deploy.sh   # Generate + commit + push
```
Vercel auto-deploys on git push (git integration configured in Vercel dashboard).

### 2. GitHub Actions (recommended for production)
`.github/workflows/daily-digest.yml` runs on schedule: 7:00 AM and 6:00 PM UTC.

**Required GitHub secrets:**
- `OPENROUTER_API_KEY` — for AI summaries (optional, falls back to no-AI mode)
- `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID` — only if NOT using Vercel's GitHub integration

**Recommended:** Use Vercel's native GitHub integration (auto-deploys on push) instead of the Vercel CLI step. Then only `OPENROUTER_API_KEY` is needed.

### 3. System cron (self-hosted)
```bash
./scripts/cron-install.sh   # Installs 7am + 6pm cron jobs
```
Logs: `logs/digest.log`

## Pipeline Steps
1. `python digest.py` — fetch Reddit + HN + RSS, generate AI summary, write `output/YYYY-MM-DD/digest.json`
2. Copy `digest.json` → `ai-digest-reader/public/data/digest.json`
3. `npm run build` — build Astro static site
4. `git commit + push` — triggers Vercel auto-deploy

## Environment Variables
See `.env.example` for full reference. Copy to `.env` for local use.

## Future OpenClaw-backed operation

AI Digest may support an explicit OpenClaw engine mode for Telegram and cron runs:

```bash
AI_DIGEST_ENGINE=openclaw ./scripts/generate-and-deploy.sh
```

This mode should be opt-in only. It must not silently use OpenClaw-managed API keys, parent-shell credentials, or another project's environment. A run preflight should print the selected engine, stages, fallback policy, and credential source category without revealing secrets.

Recommended cron rule:

- use an explicit config/env file for cron
- fail clearly if engine configuration is ambiguous
- validate `digest.json` before copy/build/commit/push
- do not deploy if OpenClaw mode was requested and the OpenClaw summary is missing or invalid

Implementation plan: [`openclaw-engine-integration-plan.md`](openclaw-engine-integration-plan.md).
