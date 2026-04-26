# Automation & CI/CD Architecture

## Overview
DailyDigest can be run manually or automatically via OpenClaw/Dexter cron. GitHub Actions scheduling has been removed so scheduled production runs can use local OpenClaw model routing and reporting.

## Deployment Modes

### 1. Manual (developer)
```bash
./scripts/setup.sh           # First time only
./scripts/generate-and-deploy.sh   # Generate + commit + push
```
Vercel auto-deploys on git push (git integration configured in Vercel dashboard).

### 2. OpenClaw/Dexter cron (production)

OpenClaw cron runs the digest at 8:00 AM and 5:00 PM Pacific. This is preferred over GitHub Actions because it can use Dexter/OpenClaw model routing and failure reporting.

Required explicit mode:

```bash
AI_DIGEST_ENGINE=openclaw \
AI_DIGEST_OPENCLAW_STAGES=summary \
AI_DIGEST_REQUIRE_SUMMARY=1 \
./scripts/generate-and-deploy.sh
```

Runbook: `scripts/openclaw-cron-run.md`.

### 3. System cron (legacy/self-hosted)
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

## OpenClaw-backed operation

AI Digest supports an explicit OpenClaw engine mode for Telegram and cron runs:

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
