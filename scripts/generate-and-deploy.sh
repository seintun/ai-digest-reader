#!/usr/bin/env bash
# Generate digest and deploy to Vercel
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

LOCK_DIR="${AI_DIGEST_LOCK_DIR:-/tmp/dailydigest-generate-and-deploy.lock}"
LOCK_STALE_AFTER_SECONDS="${AI_DIGEST_LOCK_STALE_AFTER_SECONDS:-14400}" # 4h default
LOCK_ACQUIRED=0

is_pid_alive() {
  local pid="${1:-}"
  [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null
}

lock_age_seconds() {
  local path="$1"
  local now mtime
  now="$(date +%s)"
  if mtime="$(stat -f %m "$path" 2>/dev/null)"; then
    echo $((now - mtime))
  elif mtime="$(stat -c %Y "$path" 2>/dev/null)"; then
    echo $((now - mtime))
  else
    echo 0
  fi
}

write_lock_metadata() {
  {
    echo "pid=$$"
    echo "started_at_epoch=$(date +%s)"
    echo "started_at_iso=$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    echo "host=$(hostname 2>/dev/null || echo unknown)"
    echo "cwd=$PWD"
    printf 'cmdline='
    printf '%q ' "$0" "$@"
    echo
  } > "$LOCK_DIR/owner"
}

explain_existing_lock() {
  echo "Another generate-and-deploy run is already active or a stale lock exists."
  echo "Lock: $LOCK_DIR"
  if [ -f "$LOCK_DIR/owner" ]; then
    echo "Lock owner metadata:"
    sed 's/^/  /' "$LOCK_DIR/owner" || true
  else
    echo "Lock has no owner metadata."
  fi
}

acquire_lock() {
  if mkdir "$LOCK_DIR" 2>/dev/null; then
    LOCK_ACQUIRED=1
    write_lock_metadata "$@"
    return 0
  fi

  local owner_pid=""
  if [ -f "$LOCK_DIR/owner" ]; then
    owner_pid="$(awk -F= '$1 == "pid" {print $2; exit}' "$LOCK_DIR/owner" 2>/dev/null || true)"
  fi

  if is_pid_alive "$owner_pid"; then
    explain_existing_lock
    echo "Owner PID $owner_pid is still running. Exiting without changes."
    return 1
  fi

  local age
  age="$(lock_age_seconds "$LOCK_DIR")"
  if [ "$age" -lt "$LOCK_STALE_AFTER_SECONDS" ]; then
    explain_existing_lock
    echo "No live owner PID was found, but the lock is only ${age}s old (< ${LOCK_STALE_AFTER_SECONDS}s stale threshold). Exiting without changes."
    return 1
  fi

  local stale_path="${LOCK_DIR}.stale.$(date '+%Y%m%d-%H%M%S')"
  echo "Recovering stale generate-and-deploy lock: $LOCK_DIR -> $stale_path"
  if mv "$LOCK_DIR" "$stale_path" 2>/dev/null && mkdir "$LOCK_DIR" 2>/dev/null; then
    LOCK_ACQUIRED=1
    write_lock_metadata "$@"
    return 0
  fi

  explain_existing_lock
  echo "Failed to recover stale lock safely. Exiting without changes."
  return 1
}

cleanup_lock() {
  if [ "$LOCK_ACQUIRED" = "1" ]; then
    rm -f "$LOCK_DIR/owner" 2>/dev/null || true
    rmdir "$LOCK_DIR" 2>/dev/null || true
  fi
}

acquire_lock "$@"
trap cleanup_lock EXIT

TODAY="$(date '+%Y-%m-%d')"
RUN_TIME="$(date '+%H%M%S')"
RUN_LOG_DIR="output/$TODAY"
RUN_LOG="$RUN_LOG_DIR/run-$RUN_TIME.log"
LATEST_RUN_JSON="output/latest-run.json"
mkdir -p "$RUN_LOG_DIR" output

exec > >(tee -a "$RUN_LOG") 2>&1

write_latest_run() {
  local status="$1"
  local phase="${2:-unknown}"
  local message="${3:-}"
  python3 - "$LATEST_RUN_JSON" "$status" "$phase" "$message" "$RUN_LOG" <<'PYJSON'
import json, sys, datetime
path, status, phase, message, run_log = sys.argv[1:]
payload = {
    "status": status,
    "phase": phase,
    "message": message,
    "run_log": run_log,
    "updated_at": datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z"),
}
with open(path, "w", encoding="utf-8") as f:
    json.dump(payload, f, indent=2)
    f.write("\n")
PYJSON
}

on_error() {
  local line="$1"
  echo ""
  echo "ERROR: pipeline failed at $(date '+%Y-%m-%d %H:%M:%S')"
  echo "Failed phase: ${CURRENT_PHASE:-unknown}"
  echo "Failed line: $line"
  echo "Run log: $RUN_LOG"
  write_latest_run "failed" "${CURRENT_PHASE:-unknown}" "failed at line $line"
}
trap 'on_error $LINENO' ERR
CURRENT_PHASE="preflight"
write_latest_run "started" "$CURRENT_PHASE" "run started"

# Load .env if present, but do not let blank placeholder values clobber
# real environment values supplied by the shell/cron/OpenClaw.
# shellcheck source=scripts/load-env.sh
source "$REPO_ROOT/scripts/load-env.sh"
load_env_preserve_existing ".env"

# In OpenClaw-owned production mode, semantic ranker quality scoring should use
# OpenClaw model routing, not the app's project OpenRouter key. Failures fall
# back to deterministic engagement/recency/cross-source ranking.
if [ "${AI_DIGEST_ENGINE:-standalone}" = "openclaw" ]; then
  if [ -z "${AI_DIGEST_RANKER_PROVIDER+x}" ] && [ -z "${RANKER_AI_PROVIDER+x}" ]; then
    export AI_DIGEST_RANKER_PROVIDER=openclaw
  fi
  if [ -z "${RANKER_AI_ENABLED+x}" ]; then
    export RANKER_AI_ENABLED=1
  fi
fi

preflight() {
  echo "[preflight] Checking runtime, config, git, and deployment prerequisites..."
  [ -x .venv/bin/python ] || { echo "ERROR: .venv/bin/python not found or not executable"; return 1; }
  [ -f scripts/validate-digest.py ] || { echo "ERROR: scripts/validate-digest.py not found"; return 1; }
  [ -d ai-digest-reader ] || { echo "ERROR: frontend directory ai-digest-reader not found"; return 1; }

  .venv/bin/python - <<'PYCONF'
from engine.config import load_engine_config, render_preflight
config = load_engine_config()
print(render_preflight(config))
PYCONF

  if [ "${AI_DIGEST_ENGINE:-standalone}" = "openclaw" ] && [[ ",${AI_DIGEST_OPENCLAW_STAGES:-summary}," == *",notebooklm_ingest,"* ]]; then
    local notebooklm_home="${AI_DIGEST_NOTEBOOKLM_HOME:-${NOTEBOOKLM_HOME:-}}"
    if [ -z "$notebooklm_home" ] && [ -d "$HOME/.notebooklm-flyingbacon808" ]; then
      notebooklm_home="$HOME/.notebooklm-flyingbacon808"
    fi
    if [ -z "$notebooklm_home" ] || [ ! -d "$notebooklm_home" ]; then
      echo "ERROR: NotebookLM ingest requested but profile path is missing. Set AI_DIGEST_NOTEBOOKLM_HOME or create ~/.notebooklm-flyingbacon808"
      return 1
    fi
    echo "NotebookLM profile: $notebooklm_home"
  fi

  if [ -n "$(git status --porcelain)" ]; then
    echo "ERROR: git working tree is dirty before generation. Commit/stash first so deploy cannot fail late."
    git status --short
    return 1
  fi

  git ls-remote --exit-code origin HEAD >/dev/null
  git pull --rebase
  echo "[preflight] OK"
}

preflight

echo "=== DailyDigest: Generate & Deploy ==="
echo "Started: $(date '+%Y-%m-%d %H:%M:%S')"
echo "Run log: $RUN_LOG"
echo ""

# Step 1: Generate
CURRENT_PHASE="generate"
write_latest_run "running" "$CURRENT_PHASE" "generating digest"
echo "[1/4] Generating digest..."
.venv/bin/python digest.py
echo ""

# Step 2: Validate and copy to frontend
CURRENT_PHASE="validate"
write_latest_run "running" "$CURRENT_PHASE" "validating digest"
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
CURRENT_PHASE="build"
write_latest_run "running" "$CURRENT_PHASE" "building frontend"
echo "[3/4] Building frontend..."
cd ai-digest-reader
npm run build --silent
cd ..
echo "Build complete"
echo ""

# Step 4: Commit & push (triggers Vercel auto-deploy)
CURRENT_PHASE="commit_push"
write_latest_run "running" "$CURRENT_PHASE" "committing and pushing"
echo "[4/4] Committing..."
# Stage changes first so pull --rebase won't fail on dirty worktree
git add ai-digest-reader/public/data/digest.json
[ -f reddit-cache.json ] && git add reddit-cache.json
if git diff --cached --quiet; then
  echo "No changes to digest.json, skipping commit"
else
  git commit -m "chore: update digest $(date '+%Y-%m-%d %H:%M')"
  git push
  echo "Pushed — Vercel will auto-deploy"
fi

echo ""
write_latest_run "succeeded" "done" "completed successfully"
echo "✓ Done! $(date '+%H:%M:%S')"
