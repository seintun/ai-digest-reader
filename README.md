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
python digest.py

# Generate without AI summary
python digest.py --no-ai

# Custom output directory
python digest.py --output-dir my-digests/

# Limit posts per source
python digest.py --limit 5

# Fetch specific subreddits only
python digest.py --subreddits ArtificialIntelligence LocalLLaMA

# Combine options
python digest.py --no-ai --limit 10 --output-dir ./output
```

## Output

Two files are generated per run:

```
output/
└── 2026-04-15/
    ├── digest-2026-04-15-090000.md   ← Human-readable digest
    └── digest.json                   ← Structured data (for web reader)
```

### Deploy to frontend

After generating, copy the JSON to the web reader:

```bash
cp output/$(date +%Y-%m-%d)/digest.json ai-digest-reader/public/data/digest.json
```

### JSON Output (digest.json)

The JSON file contains structured data including:

- Schema version (`v: 2`)
- Stories from Reddit and Hacker News
- AI-generated summary (if Claude CLI is available)

Each story object now includes discussion/source links and optional body text:

- `u`: original external URL (or fallback discussion URL)
- `p`: discussion permalink (`reddit.com/...` or `news.ycombinator.com/item?...`)
- `b`: plain-text body excerpt (`selftext` on Reddit or `text` on HN)

Frontend behavior uses `p` as the primary click target and keeps `u` as a visible secondary external link.

```json
{
  "v": 2,
  "d": "2026-04-15",
  "g": "2026-04-15T08:30:00+00:00",
  "r": [...],
  "h": [...],
  "summary": {
    "schema_version": "2",
    "simple": "2-3 sentence TL;DR",
    "structured": {
      "themes": ["Theme 1", "Theme 2", "Theme 3"],
      "breaking": "One sentence.",
      "mustRead": [{"id": "rd-0", "title": "Story title", "url": "https://...", "reason": "Why it matters."}]
    },
    "fullBrief": {
      "intro": "Opening paragraph.",
      "sections": [{"heading": "Section Title", "body": "Paragraph text."}],
      "closing": "One-sentence takeaway."
    }
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
| `digest.py` | Main entry point - generates digest with AI summary |
| `analyzer.py` | Generate AI summaries via Claude CLI; validates output with one-retry on schema failure |
| `schema.py` | Single source of truth: `DigestSummary` TypedDict contract and `validate_summary()` |
| `fetchers/` | Reddit and HN API integration |
| `formatter.py` | Markdown output formatting |
| `config.py` | Configuration (subreddits, limits) |

## Sources

- Reddit: r/ArtificialIntelligence, r/LocalLLaMA, r/ChatGPT, r/MachineLearning
- Hacker News: Front page

## Troubleshooting

See [TROUBLESHOOTING.md](ai-digest-reader/docs/TROUBLESHOOTING.md) for common issues.
