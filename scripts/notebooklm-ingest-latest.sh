#!/usr/bin/env bash
set -euo pipefail

CAP=100
ACCOUNT=""
NOTEBOOKLM_HOME_ARG=""
DIGEST_PATH=""
DATE_ARG=""
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RESEARCH_ENGINE_ROOT="${RESEARCH_ENGINE_ROOT:-$HOME/.openclaw/workspace/projects/research-engine}"

usage() {
  cat <<'EOF'
Usage: scripts/notebooklm-ingest-latest.sh [--cap 100] [--account flyingbacon808] [--notebooklm-home PATH] [--digest PATH] [--date YYYY-MM-DD]

Robustly ingests the latest AI digest into NotebookLM:
  - uses only top N ranked digest items
  - writes to the selected NotebookLM auth profile when provided
  - retries failed URL imports as text fallback sources
  - prunes duplicate/error placeholder sources
  - verifies exact top-N coverage and no extras
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --cap) CAP="$2"; shift 2 ;;
    --account) ACCOUNT="$2"; shift 2 ;;
    --notebooklm-home) NOTEBOOKLM_HOME_ARG="$2"; shift 2 ;;
    --digest) DIGEST_PATH="$2"; shift 2 ;;
    --date) DATE_ARG="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage >&2; exit 2 ;;
  esac
done

if [[ -n "$NOTEBOOKLM_HOME_ARG" ]]; then
  export NOTEBOOKLM_HOME="$NOTEBOOKLM_HOME_ARG"
elif [[ -n "$ACCOUNT" && -d "$HOME/.notebooklm-$ACCOUNT" ]]; then
  export NOTEBOOKLM_HOME="$HOME/.notebooklm-$ACCOUNT"
elif [[ -n "$ACCOUNT" ]]; then
  echo "ERROR: requested NotebookLM account profile $HOME/.notebooklm-$ACCOUNT not found; refusing to use ambient auth" >&2
  echo "Create/login that profile or pass --notebooklm-home PATH explicitly." >&2
  exit 1
fi

if [[ -n "${NOTEBOOKLM_HOME:-}" && ! -d "$NOTEBOOKLM_HOME" ]]; then
  echo "ERROR: NOTEBOOKLM_HOME does not exist: $NOTEBOOKLM_HOME" >&2
  exit 1
fi

if [[ -z "$DIGEST_PATH" ]]; then
  if [[ -n "$DATE_ARG" ]]; then
    DIGEST_PATH="$ROOT_DIR/output/$DATE_ARG/digest.json"
  else
    DIGEST_PATH="$(find "$ROOT_DIR/output" -path '*/digest.json' -type f -print0 2>/dev/null | xargs -0 ls -t 2>/dev/null | head -1 || true)"
  fi
fi

if [[ -z "$DIGEST_PATH" || ! -f "$DIGEST_PATH" ]]; then
  echo "No digest.json found. Provide --digest PATH or run the digest first." >&2
  exit 1
fi

if [[ ! -x "$RESEARCH_ENGINE_ROOT/.venv/bin/python" ]]; then
  echo "research-engine venv not found at $RESEARCH_ENGINE_ROOT/.venv/bin/python" >&2
  exit 1
fi

DIGEST_DIR="$(cd "$(dirname "$DIGEST_PATH")" && pwd)"
POSTS_JSON="$DIGEST_DIR/notebooklm-top${CAP}-posts.json"
REPORT_JSON="$DIGEST_DIR/notebooklm-ingest.json"
VERIFY_JSON="$DIGEST_DIR/notebooklm-top${CAP}-verification.json"

python3 - "$DIGEST_PATH" "$CAP" "$POSTS_JSON" <<'PY'
import json, pathlib, sys
path = pathlib.Path(sys.argv[1])
cap = int(sys.argv[2])
out = pathlib.Path(sys.argv[3])
d = json.load(open(path))
posts = (d.get('r', []) + d.get('h', []) + d.get('rs', []))[:cap]
out.write_text(json.dumps(posts), encoding='utf-8')
print(f"prepared {len(posts)} posts from {path} -> {out}")
PY

cd "$RESEARCH_ENGINE_ROOT"
.venv/bin/python -m research_engine.cli notebooklm-ingest \
  --input "$POSTS_JSON" \
  --output "$REPORT_JSON" \
  --max-sources "$CAP" \
  --robust

python3 - "$DIGEST_PATH" "$REPORT_JSON" "$VERIFY_JSON" "$CAP" <<'PY'
import json, pathlib, sys

digest_path = pathlib.Path(sys.argv[1])
report_path = pathlib.Path(sys.argv[2])
verify_path = pathlib.Path(sys.argv[3])
cap = int(sys.argv[4])
report = json.load(open(report_path))
verification = report.get('verification') or {}
verify_path.write_text(json.dumps(verification, indent=2), encoding='utf-8')

d = json.load(open(digest_path))
d.setdefault('metrics', {})['notebook_ingest'] = {
    'enabled': True,
    'added': verification.get('source_count', len(report.get('added', []))),
    'skipped': len(report.get('to_skip', [])) + len(report.get('deferred', [])),
    'failed': len(report.get('fallback_failed', [])),
    'dry_run': False,
    'notebook_id': report.get('notebook_id'),
    'notebook_url': report.get('notebook_url'),
    'error': None if report.get('ok') else 'NotebookLM verification failed',
    'cap': cap,
    'source_count_verified': verification.get('source_count'),
    'top_covered': verification.get('covered'),
    'fallback_sources': verification.get('fallback_sources'),
    'verification_ok': bool(report.get('ok')),
}
digest_path.write_text(json.dumps(d, indent=2), encoding='utf-8')
print(json.dumps({
    'ok': bool(report.get('ok')),
    'notebook_url': report.get('notebook_url'),
    'source_count': verification.get('source_count'),
    'covered': verification.get('covered'),
    'fallback_sources': verification.get('fallback_sources'),
    'missing': len(verification.get('missing', [])),
    'extras': len(verification.get('extras', [])),
    'verification': str(verify_path),
}, indent=2))
if not report.get('ok'):
    raise SystemExit(1)
PY
