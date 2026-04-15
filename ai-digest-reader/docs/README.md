# AI Digest Reader

A mobile-first PWA news reader that aggregates AI-related content from Reddit and Hacker News into a clean, personalized digest with AI-generated summaries.

## Features

- **Multi-source aggregation** - Combines posts from Reddit (r/ArtificialIntelligence, r/LocalLLaMA, r/ChatGPT, r/MachineLearning) and Hacker News
- **AI Summary** - Claude-powered daily briefings with themes, breaking news, and must-read articles
- **Tabbed summary display** - Quick overview, themes, breaking news, and must-read in a tabbed interface
- **Three view modes** - Cards, list, and glance views for different browsing preferences
- **Source filtering** - Filter content by Reddit, Hacker News, or view all
- **Dark mode** - Automatic theme detection with manual toggle
- **Offline support** - PWA with service worker caching
- **Responsive design** - Mobile-first approach with desktop support

## Quick Start

### Frontend (Astro)

```bash
# Install dependencies
cd ai-digest-reader
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Backend (Python Digest Generator)

```bash
# Create virtual environment
python3 -m venv venv

# Activate venv
source venv/bin/activate  # macOS/Linux
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install requests

# Generate digest JSON with AI summary (requires Claude CLI)
python digest.py

# Generate without AI summary
python digest.py --no-ai

# Generate and save to public/data/digest.json
python digest.py --output-dir ai-digest-reader/public/data/
```

### Prerequisites for AI Summaries

Install Claude CLI for AI-powered summaries:

```bash
# macOS
brew install anthropic/anthropic/claude

# or via npm
npm install -g @anthropic-ai/claude

# Verify
claude --version
```

### Running with Sample Data

The project includes sample data at `public/data/digest.json`. After generating your own data, the JSON is printed to stdout - redirect it to the data file:

```bash
python scripts/generator.py > public/data/digest.json
```

## AI Summary Feature

The digest reader displays AI-generated summaries created by Claude:

| Tab | Content |
|-----|---------|
| **Overview** | One-line summary of the day's AI news |
| **Themes** | Key themes and trends identified |
| **Breaking** | Urgent or important breaking news |
| **Must-Read** | Curated essential articles with reasons |

### Summary Generation

Summaries are generated during digest creation using `analyzer.py`:

1. Stories are collected from Reddit and Hacker News
2. Claude CLI analyzes the stories
3. Structured summary is generated with themes, breaking news, and must-read items
4. Summary is included in `digest.json` (schema v2)

### Without AI Summary

If Claude CLI is unavailable, use `--no-ai`:

```bash
python digest.py --no-ai
```

This generates a v1-compatible digest without the AI summary field.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Astro 5, Tailwind CSS 3, Vanilla JavaScript |
| Backend | Python CLI (data generation + AI analysis) |
| AI Summaries | Claude CLI (Anthropic) |
| Deployment | Vercel |
| Data | JSON (schema v2) |

## Project Structure

```
ai-digest-reader/
├── src/
│   ├── pages/
│   │   └── api/digest.ts    ← Serverless API endpoint
│   ├── components/
│   │   ├── DigestSummary.astro  ← AI summary display
│   │   └── ...
│   └── layouts/
├── public/
│   └── data/digest.json     ← Pre-generated digest data
├── package.json
└── vercel.json
```

## Screenshots

*Coming soon*

### Card View with AI Summary
![Card View Placeholder]

### Summary Tabs
![Summary Display Placeholder]

### List View
![List View Placeholder]

## Documentation

- [Architecture](ARCHITECTURE.md)
- [Data Schema](DATA_SCHEMA.md)
- [Troubleshooting](TROUBLESHOOTING.md)
- [Changelog](CHANGELOG.md)
