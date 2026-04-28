#!/usr/bin/env bash
# Generate digest and deploy to Vercel
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

LOCK_DIR="/tmp/dailydigest-generate-and-deploy.lock"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "Another generate-and-deploy run is already active (lock: $LOCK_DIR). Exiting."
  exit 1
fi
trap 'rmdir "$LOCK_DIR" 2>/dev/null || true' EXIT

TODAY="$(date '+%Y-%m-%d')"
RUN_TIME="$(date '+%H%M%S')"
RUN_LOG_DIR="output/$TODAY"
RUN_LOG="$RUN_LOG_DIR/run-$RUN_TIME.log"
mkdir -p "$RUN_LOG_DIR"

exec > >(tee -a "$RUN_LOG") 2>&1

on_error() {
  echo ""
  echo "ERROR: pipeline failed at $(date '+%Y-%m-%d %H:%M:%S')"
  echo "Run log: $RUN_LOG"
}
trap on_error ERR

# Load .env if present, but do not let blank placeholder values clobber
# real environment values supplied by the shell/cron/OpenClaw.
# shellcheck source=scripts/load-env.sh
source "$REPO_ROOT/scripts/load-env.sh"
load_env_preserve_existing ".env"

# In OpenClaw-owned production mode, do not let the app's ranking step spend
# project OpenRouter credits. Summary/NotebookLM stages are handled by OpenClaw;
# ranking falls back to deterministic engagement/recency/cross-source signals
# unless Rickie explicitly opts back in with RANKER_AI_ENABLED=1.
if [ "${AI_DIGEST_ENGINE:-standalone}" = "openclaw" ] && [ -z "${RANKER_AI_ENABLED+x}" ]; then
  export RANKER_AI_ENABLED=0
fi

echo "=== DailyDigest: Generate & Deploy ==="
echo "Started: $(date '+%Y-%m-%d %H:%M:%S')"
echo "Run log: $RUN_LOG"
echo ""

# Step 1: Generate
echo "[1/4] Generating digest..."
.venv/bin/python digest.py
echo ""

# Step 2: Validate and copy to frontend
echo "[2/4] Validating and copying digest to frontend..."
DIGEST_SRC="output/$TODAY/digest.json"
DIGEST_DST="ai-digest-reader/public/data/digest.json"

if [ ! -f "$DIGEST_SRC" ]; then
  echo "ERROR: Expected digest at $DIGEST_SRC but not found"
  exit 1
fi

VALIDATE_ARGS=()
if [ "${AI_DIGEST_REQUIRE_SUMMARY:-1}" = "1" ]; then
  VALIDATE_ARGS+=(--require-summary)
fi
.venv/bin/python scripts/validate-digest.py "$DIGEST_SRC" "${VALIDATE_ARGS[@]}"

cp "$DIGEST_SRC" "$DIGEST_DST"
echo "Copied: $DIGEST_SRC → $DIGEST_DST"
echo ""

# Step 3: Build
echo "[3/4] Building frontend..."
cd ai-digest-reader
npm run build --silent
cd ..
echo "Build complete"
echo ""

# Step 4: Commit & push (triggers Vercel auto-deploy)
echo "[4/4] Committing..."
# Stage changes first so pull --rebase won't fail on dirty worktree
git add ai-digest-reader/public/data/digest.json
[ -f reddit-cache.json ] && git add reddit-cache.json
git pull --rebase
if git diff --cached --quiet; then
  echo "No changes to digest.json, skipping commit"
else
  git commit -m "chore: update digest $(date '+%Y-%m-%d %H:%M')"
  git push
  echo "Pushed — Vercel will auto-deploy"
fi

echo ""
echo "✓ Done! $(date '+%H:%M:%S')"
