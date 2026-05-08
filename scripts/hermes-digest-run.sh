#!/usr/bin/env bash
# Hermes-owned wrapper for scheduler-driven AI Digest runs.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

MODE="${AI_DIGEST_HERMES_MODE:-validate-only}"
NO_AI="${AI_DIGEST_NO_AI:-0}"
LIMIT="${AI_DIGEST_LIMIT:-}"
STATUS="started"

summary_json() {
  python3 - "$@" <<'PY'
import json, sys, datetime
mode, status, exit_code, run_log = sys.argv[1:5]
payload = {
    "wrapper": "hermes-digest-run",
    "mode": mode,
    "status": status,
    "exit_code": int(exit_code),
    "run_log": run_log,
    "timestamp": datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z"),
}
print(json.dumps(payload, separators=(",", ":")))
PY
}

RUN_LOG="output/hermes-digest-run.$(date +%Y%m%d-%H%M%S).log"
mkdir -p output
exec > >(tee -a "$RUN_LOG") 2>&1

echo "[hermes] digest wrapper starting"
echo "[hermes] mode=$MODE"

if [ "$MODE" = "validate-only" ]; then
  export AI_DIGEST_DEPLOY_MODE=validate-only
  export AI_DIGEST_OPENCLAW_STAGES=summary
  if [ "$NO_AI" = "1" ]; then
    export AI_DIGEST_NO_AI=1
  fi
  if [ -n "$LIMIT" ]; then
    export AI_DIGEST_LIMIT="$LIMIT"
  fi
else
  export AI_DIGEST_DEPLOY_MODE=full
fi

if ./scripts/generate-and-deploy.sh; then
  EXIT_CODE=0
  STATUS="succeeded"
else
  EXIT_CODE=$?
  STATUS="failed"
fi

echo "$(summary_json "$MODE" "$STATUS" "$EXIT_CODE" "$RUN_LOG")"
exit "$EXIT_CODE"