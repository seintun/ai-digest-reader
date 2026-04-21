#!/usr/bin/env bash
# Generate digest and deploy to Vercel
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Load .env if present
if [ -f ".env" ]; then
  set -a
  # shellcheck source=.env
  source .env
  set +a
fi

echo "=== DailyDigest: Generate & Deploy ==="
echo "Started: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# Step 1: Generate
echo "[1/4] Generating digest..."
.venv/bin/python digest.py
echo ""

# Step 2: Copy to frontend
echo "[2/4] Copying digest to frontend..."
TODAY=$(date '+%Y-%m-%d')
DIGEST_SRC="output/$TODAY/digest.json"
DIGEST_DST="ai-digest-reader/public/data/digest.json"

if [ ! -f "$DIGEST_SRC" ]; then
  echo "ERROR: Expected digest at $DIGEST_SRC but not found"
  exit 1
fi

cp "$DIGEST_SRC" "$DIGEST_DST"
echo "Copied: $DIGEST_SRC → $DIGEST_DST"
echo ""

# Step 3: Build
echo "[3/4] Building frontend..."
cd ai-digest-reader
npm run build --silent
cd ..
echo "Build complete"
echo ""

# Step 4: Commit & push (triggers Vercel auto-deploy)
echo "[4/4] Committing..."
git add ai-digest-reader/public/data/digest.json
if git diff --cached --quiet; then
  echo "No changes to digest.json, skipping commit"
else
  git commit -m "chore: update digest $(date '+%Y-%m-%d %H:%M')"
  git push
  echo "Pushed — Vercel will auto-deploy"
fi

echo ""
echo "✓ Done! $(date '+%H:%M:%S')"
