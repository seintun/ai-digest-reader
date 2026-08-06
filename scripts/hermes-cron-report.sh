#!/usr/bin/env bash
# Deterministic Hermes cron entrypoint: runs one digest pipeline and emits one report.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

MODE="full"
if [ "${1:-}" = "--check-only" ]; then
  MODE="check-only"
elif [ "$#" -ne 0 ]; then
  echo "Usage: scripts/hermes-cron-report.sh [--check-only]"
  exit 2
fi

export AI_DIGEST_ENGINE=openclaw
export AI_DIGEST_OPENCLAW_STAGES=summary,notebooklm_ingest
export AI_DIGEST_SUMMARY_PROVIDER=hermes
export AI_DIGEST_REQUIRE_SUMMARY=1
export AI_DIGEST_RANKER_PROVIDER=openclaw
export RANKER_AI_ENABLED=1
export AI_DIGEST_HERMES_COMMAND=hermes
export AI_DIGEST_HERMES_PROVIDER=omniroute
export AI_DIGEST_HERMES_MODEL=codex-combo
export AI_DIGEST_ANALYSIS_ENABLED=1

RUN_OUTPUT="$(mktemp)"
trap 'rm -f "$RUN_OUTPUT"' EXIT

if bash ./scripts/hermes-digest-run.sh "--$MODE" >"$RUN_OUTPUT" 2>&1; then
  PIPELINE_OK=1
else
  PIPELINE_OK=0
fi

python3 - "$RUN_OUTPUT" "$PIPELINE_OK" <<'PY'
import json
import sys
from pathlib import Path

run_output = Path(sys.argv[1]).read_text(errors="replace")
pipeline_ok = sys.argv[2] == "1"

report = None
for line in reversed(run_output.splitlines()):
    try:
        candidate = json.loads(line)
    except json.JSONDecodeError:
        continue
    if candidate.get("wrapper") == "hermes-digest-run":
        report = candidate
        break

if not pipeline_ok or not report or report.get("status") != "succeeded":
    run_log = report.get("run_log") if report else None
    details = "pipeline did not produce a successful report"
    for line in reversed(run_output.splitlines()):
        if line.startswith("ERROR:") or "already active" in line or "stale lock" in line:
            details = line
            break
    suffix = f" Log: {run_log}." if run_log else ""
    print(f"❌ AI Digest failed — {details}.{suffix}")
    raise SystemExit(1)

digest_path = Path(report.get("digest_path", "ai-digest-reader/public/data/digest.json"))
if not digest_path.is_file():
    print(f"❌ AI Digest failed — digest artifact missing: {digest_path}.")
    raise SystemExit(1)

try:
    digest = json.loads(digest_path.read_text())
except (OSError, json.JSONDecodeError) as exc:
    print(f"❌ AI Digest failed — could not read digest artifact: {exc}.")
    raise SystemExit(1)

summary = digest.get("summary", digest)
structured = summary.get("structured", {}) if isinstance(summary, dict) else {}
lines = []
date = digest.get("d") or digest.get("date")
if date:
    lines.append(f"📰 AI Digest — {date}")

simple = summary.get("simple") if isinstance(summary, dict) else None
if simple:
    lines.append(str(simple))

breaking = structured.get("breaking") if isinstance(structured, dict) else None
if breaking:
    lines.append(f"🔥 {breaking}")

must_read = structured.get("mustRead", []) if isinstance(structured, dict) else []
if isinstance(must_read, list):
    for item in must_read[:3]:
        if not isinstance(item, dict):
            continue
        title = item.get("title")
        url = item.get("url")
        if title and url:
            lines.append(f"[{title}]({url})")

analysis = summary.get("analysis") if isinstance(summary, dict) else None
if isinstance(analysis, dict) and analysis.get("skeptic_take"):
    confidence = analysis.get("confidence")
    prefix = f"🧭 Analysis (confidence: {confidence}):" if confidence is not None else "🧭 Analysis:"
    lines.append(f"{prefix} {analysis['skeptic_take']}")

warnings = report.get("quality_gate", {}).get("warnings", [])
if warnings:
    lines.append("⚠️ Quality:")
    lines.extend(str(warning) for warning in warnings)

lines.append("Full briefing: https://dailydigest.vercel.app")
print("\n".join(lines))
PY
