#!/usr/bin/env bash
# Install Hermes-owned twice-daily cron jobs for AI Digest
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HERMES_SCRIPT="$REPO_ROOT/scripts/hermes-digest-run.sh"
LOG_DIR="$REPO_ROOT/logs"

mkdir -p "$LOG_DIR"

ENTRY_MORNING="0 8 * * * AI_DIGEST_ENGINE=openclaw AI_DIGEST_OPENCLAW_STAGES=summary,notebooklm_ingest AI_DIGEST_SUMMARY_PROVIDER=hermes AI_DIGEST_REQUIRE_SUMMARY=1 AI_DIGEST_RANKER_PROVIDER=openclaw RANKER_AI_ENABLED=1 AI_DIGEST_HERMES_COMMAND=hermes AI_DIGEST_HERMES_PROVIDER=omniroute AI_DIGEST_HERMES_MODEL=codex-combo $HERMES_SCRIPT --full >> $LOG_DIR/digest.log 2>&1"
ENTRY_EVENING="0 17 * * * AI_DIGEST_ENGINE=openclaw AI_DIGEST_OPENCLAW_STAGES=summary,notebooklm_ingest AI_DIGEST_SUMMARY_PROVIDER=hermes AI_DIGEST_REQUIRE_SUMMARY=1 AI_DIGEST_RANKER_PROVIDER=openclaw RANKER_AI_ENABLED=1 AI_DIGEST_HERMES_COMMAND=hermes AI_DIGEST_HERMES_PROVIDER=omniroute AI_DIGEST_HERMES_MODEL=codex-combo $HERMES_SCRIPT --full >> $LOG_DIR/digest.log 2>&1"

# Remove old entries, add new ones
(crontab -l 2>/dev/null | grep -v "generate-and-deploy\|hermes-digest-run"; echo "$ENTRY_MORNING"; echo "$ENTRY_EVENING") | crontab -

echo "✓ Cron jobs installed:"
echo "  8:00 AM daily  → $HERMES_SCRIPT (Hermes-owned production mode)"
echo "  5:00 PM daily  → $HERMES_SCRIPT (Hermes-owned production mode)"
echo "  Logs: $LOG_DIR/digest.log"
