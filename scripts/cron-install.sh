#!/usr/bin/env bash
# Install twice-daily cron jobs for DailyDigest
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$REPO_ROOT/scripts/generate-and-deploy.sh"
LOG_DIR="$REPO_ROOT/logs"

mkdir -p "$LOG_DIR"

ENTRY_MORNING="0 8 * * * AI_DIGEST_ENGINE=openclaw AI_DIGEST_OPENCLAW_STAGES=summary AI_DIGEST_REQUIRE_SUMMARY=1 $SCRIPT >> $LOG_DIR/digest.log 2>&1"
ENTRY_EVENING="0 17 * * * AI_DIGEST_ENGINE=openclaw AI_DIGEST_OPENCLAW_STAGES=summary AI_DIGEST_REQUIRE_SUMMARY=1 $SCRIPT >> $LOG_DIR/digest.log 2>&1"

# Remove old entries, add new ones
(crontab -l 2>/dev/null | grep -v "generate-and-deploy"; echo "$ENTRY_MORNING"; echo "$ENTRY_EVENING") | crontab -

echo "✓ Cron jobs installed:"
echo "  8:00 AM daily  → $SCRIPT (OpenClaw mode)"
echo "  5:00 PM daily  → $SCRIPT (OpenClaw mode)"
echo "  Logs: $LOG_DIR/digest.log"
