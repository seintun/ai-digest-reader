# AI News Digest Aggregator

Quick daily digest of hot AI content from Reddit + Hacker News with AI-generated summaries.

## Prerequisites

- **Python 3.8+**
- **pip** for installing dependencies
- **Claude CLI** (optional, for AI summaries)

### Install Claude CLI

For AI-powered summaries, install the Claude CLI:

```bash
# macOS
brew install anthropic/anthropic/claude

# or via npm
npm install -g @anthropic-ai/claude

# Verify installation
claude --version
```

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Generate today's digest with AI summary (requires Claude CLI)
python scripts/generator.py

# Generate without AI summary
python scripts/generator.py --no-ai

# Custom output directory
python scripts/generator.py --output-dir my-digests/

# Limit posts per source
python scripts/generator.py --limit 5

# Fetch specific subreddits only
python scripts/generator.py --subreddits ArtificialIntelligence LocalLLaMA

# Combine options
python scripts/generator.py --no-ai --limit 10 --output-dir ./output
```

## Output

Two files are generated per run:

```
output/
└── 2026-04-15/
    ├── digest-2026-04-15-090000.md    ← Human-readable digest
    └── digest-2026-04-15-090000.json  ← Structured data (for web reader)
```

### JSON Output (digest.json)

The JSON file contains structured data including:

- Schema version (`v: 2`)
- Stories from Reddit and Hacker News
- AI-generated summary (if Claude CLI is available)

```json
{
  "v": 2,
  "d": "2026-04-15",
  "g": "2026-04-15T08:30:00+00:00",
  "r": [...],
  "h": [...],
  "summary": {
    "simple": "One-line overview",
    "themes": ["Theme 1", "Theme 2"],
    "breaking": ["Breaking item"],
    "mustRead": [{"title": "...", "url": "...", "source": "reddit", "reason": "..."}],
    "fullBrief": "Detailed briefing..."
  }
}
```

### Markdown Output (digest.md)

Human-readable format with:
- Quick overview
- Key themes
- Breaking news
- Must-read articles
- Full story list

## Scripts

| Script | Purpose |
|--------|---------|
| `aggregator.py` | Fetch stories from Reddit + HN |
| `analyzer.py` | Generate AI summaries (Claude CLI) |
| `generator.py` | Main entry point (generates both outputs) |
| `reddit_adapter.py` | Reddit API integration |
| `hn_adapter.py` | Hacker News API integration |
| `config.py` | Shared configuration |

## Sources

- Reddit: r/ArtificialIntelligence, r/LocalLLaMA, r/ChatGPT, r/MachineLearning
- Hacker News: Front page

## Troubleshooting

See [TROUBLESHOOTING.md](ai-digest-reader/docs/TROUBLESHOOTING.md) for common issues.
