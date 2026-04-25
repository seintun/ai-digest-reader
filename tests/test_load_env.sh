#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$***REDACTED_RUBYGEMS_KEY***.sh"

tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT
cat > "$tmp" <<'ENV'
# comment
OPENROUTER_API_KEY=
OPENROUTER_MODEL="moonshotai/kimi-k2.6"
BAD KEY=value
ENV

OPENROUTER_API_KEY="real-key"
export OPENROUTER_API_KEY
unset OPENROUTER_MODEL || true
***REDACTED_RUBYGEMS_KEY*** "$tmp"

[ "$OPENROUTER_API_KEY" = "real-key" ]
[ "$OPENROUTER_MODEL" = "moonshotai/kimi-k2.6" ]

echo "load-env ok"
