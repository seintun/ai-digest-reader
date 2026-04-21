#!/usr/bin/env bash
# DailyDigest first-time setup script
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "=== DailyDigest Setup ==="
echo ""

# Python virtual environment
if [ ! -d ".venv" ]; then
  echo "Creating Python virtual environment..."
  python3 -m venv .venv
fi
echo "Installing Python dependencies..."
.venv/bin/pip install -r requirements.txt -q
echo "✓ Python ready"

# Node.js dependencies
echo "Installing frontend dependencies..."
cd ai-digest-reader && npm install --silent && cd ..
echo "✓ Frontend ready"

# Environment file
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo ""
  echo "Created .env — edit it and add your OPENROUTER_API_KEY (optional)"
fi

echo ""
echo "✓ Setup complete!"
echo "  Run digest: ./scripts/generate-and-deploy.sh"
echo "  Dev server: cd ai-digest-reader && npm run dev"
