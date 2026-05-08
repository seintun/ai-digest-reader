#!/usr/bin/env bash
# Hermes-owned wrapper for scheduler-driven AI Digest runs.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

MODE="${AI_DIGEST_HERMES_MODE:-validate-only}"
NO_AI="${AI_DIGEST_NO_AI:-0}"
LIMIT="${AI_DIGEST_LIMIT:-}"

usage() {
  cat <<'USAGE'
Usage: scripts/hermes-digest-run.sh [--full|--validate-only|--check-only] [--no-ai] [--limit N]

Modes:
  --full           Run the full generate → validate → build → push flow.
  --validate-only   Run generation and validation, but skip build and push.
  --check-only      Skip generation and validate the latest existing digest artifact.

Environment variables remain supported for compatibility:
  AI_DIGEST_HERMES_MODE, AI_DIGEST_NO_AI, AI_DIGEST_LIMIT
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --full)
      MODE="full"
      ;;
    --validate-only)
      MODE="validate-only"
      ;;
    --check-only)
      MODE="check-only"
      ;;
    --no-ai)
      NO_AI=1
      ;;
    --limit)
      shift
      [ "$#" -gt 0 ] || { echo "ERROR: --limit requires a value"; exit 2; }
      LIMIT="$1"
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument: $1"
      usage
      exit 2
      ;;
  esac
  shift
done

summary_json() {
  python3 - "$@" <<'PY'
import datetime
import json
import sys
mode, phase, status, exit_code, run_log, validated, built, pushed, digest_path = sys.argv[1:10]
payload = {
    "wrapper": "hermes-digest-run",
    "mode": mode,
    "phase": phase,
    "status": status,
    "exit_code": int(exit_code),
    "validated": validated == "1",
    "built": built == "1",
    "pushed": pushed == "1",
    "digest_path": digest_path,
    "run_log": run_log,
    "timestamp": datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z"),
}
print(json.dumps(payload, separators=(",", ":")))
PY
}

latest_digest_path() {
  python3 - <<'PY'
from pathlib import Path
candidates = []
for path in Path('output').glob('*/digest.json'):
    try:
        candidates.append((path.stat().st_mtime, path))
    except FileNotFoundError:
        pass
if not candidates:
    print('')
else:
    candidates.sort()
    print(candidates[-1][1])
PY
}

run_check_only() {
  local digest_path
  digest_path="${AI_DIGEST_DIGEST_PATH:-ai-digest-reader/public/data/digest.json}"
  if [ ! -f "$digest_path" ]; then
    digest_path="$(latest_digest_path)"
  fi
  if [ -z "$digest_path" ] || [ ! -f "$digest_path" ]; then
    echo "ERROR: no digest artifact found to validate"
    return 1
  fi

  local validate_args=()
  if [ "${AI_DIGEST_REQUIRE_SUMMARY:-1}" = "1" ]; then
    validate_args+=(--require-summary)
  fi

  .venv/bin/python scripts/validate-digest.py "$digest_path" "${validate_args[@]}"
  echo "[check-only] Validated existing digest: $digest_path"
  echo "$(summary_json "$MODE" "check" "succeeded" 0 "$RUN_LOG" 1 0 0 "$digest_path")"
}

RUN_LOG="output/hermes-digest-run.$(date +%Y%m%d-%H%M%S).log"
mkdir -p output
exec > >(tee -a "$RUN_LOG") 2>&1

echo "[hermes] digest wrapper starting"
echo "[hermes] mode=$MODE"

if [ "$MODE" = "check-only" ]; then
  run_check_only
  exit 0
fi

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

EXIT_CODE=0
STATUS="started"
PHASE="generate"
VALIDATED=0
BUILT=0
PUSHED=0
DIGEST_PATH=""

if ./scripts/generate-and-deploy.sh; then
  EXIT_CODE=0
  STATUS="succeeded"
  VALIDATED=1
  if [ "$MODE" = "full" ]; then
    BUILT=1
    PUSHED=1
  else
    BUILT=0
    PUSHED=0
  fi
else
  EXIT_CODE=$?
  STATUS="failed"
fi

DIGEST_PATH="${AI_DIGEST_DIGEST_PATH:-ai-digest-reader/public/data/digest.json}"
if [ ! -f "$DIGEST_PATH" ]; then
  DIGEST_PATH="$(latest_digest_path)"
fi

SUMMARY_JSON="$(summary_json "$MODE" "$PHASE" "$STATUS" "$EXIT_CODE" "$RUN_LOG" "$VALIDATED" "$BUILT" "$PUSHED" "$DIGEST_PATH")"

if [ "$EXIT_CODE" = "0" ] && [ -n "$DIGEST_PATH" ] && [ -f "$DIGEST_PATH" ]; then
  report_path="output/benchmarks/$(date +%Y-%m-%d)/summary-report.md"
  if [ -f "$REPO_ROOT/scripts/write_summary_benchmark_report.py" ]; then
    .venv/bin/python "$REPO_ROOT/scripts/write_summary_benchmark_report.py" "$DIGEST_PATH" "$report_path" >/dev/null
    echo "[benchmark] wrote report: $report_path"
    SUMMARY_JSON="$SUMMARY_JSON" REPORT_PATH="$report_path" python3 - <<'PY'
import json, os
payload = json.loads(os.environ["SUMMARY_JSON"])
payload["report_path"] = os.environ["REPORT_PATH"]
print(json.dumps(payload, separators=(",", ":")))
PY
  else
    echo "[benchmark] report generator unavailable; skipping report write"
    echo "$SUMMARY_JSON"
  fi
else
  echo "$SUMMARY_JSON"
fi
exit "$EXIT_CODE"
