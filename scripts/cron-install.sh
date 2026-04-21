#!/usr/bin/env bash
# Install twice-daily cron jobs for DailyDigest
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$REPO_ROOT/scripts/generate-and-deploy.sh"
LOG_DIR="$REPO_ROOT/logs"

mkdir -p "$LOG_DIR"

ENTRY_MORNING="0 7 * * * $SCRIPT >> $LOG_DIR/digest.log 2>&1"
ENTRY_EVENING="0 18 * * * $SCRIPT >> $LOG_DIR/digest.log 2>&1"

# Remove old entries, add new ones
(crontab -l 2>/dev/null | grep -v "generate-and-deploy"; echo "$ENTRY_MORNING"; echo "$ENTRY_EVENING") | crontab -

echo "✓ Cron jobs installed:"
echo "  7:00 AM daily  → $SCRIPT"
echo " 6:00 PM daily  → $SCRIPT"
echo "  Logs: $LOG_DIR/digest.log"
