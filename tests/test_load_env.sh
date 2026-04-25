#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$REPO_ROOT/scripts/load-env.sh"

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
load_env_preserve_existing "$tmp"

[ "$OPENROUTER_API_KEY" = "real-key" ]
[ "$OPENROUTER_MODEL" = "moonshotai/kimi-k2.6" ]

echo "load-env ok"
