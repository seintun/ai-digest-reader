# Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                          DATA SOURCES                                │
├─────────────────────────────────────────────────────────────────────┤
│  1. Reddit API (pushshift.io + reddit.com)                          │
│  2. Hacker News API (firebaseio.com)                                 │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    PYTHON SCRIPTS (Local/CI)                         │
├─────────────────────────────────────────────────────────────────────┤
│  ├── aggregator.py     → Fetch & merge stories                      │
│  ├── analyzer.py       → Generate AI summaries via Claude CLI       │
│  ├── generator.py      → Output JSON + MD digest files               │
│  └── config.py         → Shared configuration                        │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        DEPLOYMENT                                   │
├─────────────────────────────────────────────────────────────────────┤
│  Vercel (Serverless Functions + CDN)                               │
│  ├── /api/digest → Serve generated digest.json                      │
│  └── Static assets → CDN edge network                             │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                           CLIENT (PWA)                              │
├─────────────────────────────────────────────────────────────────────┤
│  Astro SSR + Tailwind CSS                                          │
│  ├── DigestSummary component (tabbed summary display)               │
│  ├── Client-side caching (localStorage)                            │
│  ├── Theme detection (dark/light mode)                             │
│  └── View state persistence                                         │
└─────────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
dailydigest/
├── ai-digest-reader/     ← Vercel deployment target (THIS IS DEPLOYED)
│   ├── src/
│   │   ├── pages/api/   ← /api/digest serverless endpoint
│   │   └── components/  ← Astro components
│   │       └── DigestSummary.astro ← AI summary display
│   ├── public/
│   │   └── data/        ← digest.json (generated daily)
│   ├── package.json
│   ├── astro.config.mjs
│   └── vercel.json
├── scripts/              ← Python CLI (local/CI, NOT deployed to Vercel)
│   ├── aggregator.py    ← Fetch from Reddit + HN
│   ├── analyzer.py      ← AI summary generation via Claude CLI
│   ├── generator.py     ← Generate JSON/MD output
│   ├── reddit_adapter.py
│   ├── hn_adapter.py
│   ├── base.py
│   └── config.py
├── docs/
│   ├── ARCHITECTURE.md
│   ├── DATA_SCHEMA.md
│   ├── README.md
│   ├── TROUBLESHOOTING.md
│   ├── CHANGELOG.md
│   └── diagrams/
│       ├── ARCHITECTURE.txt
│       ├── DATA_FLOW.txt
│       └── SUMMARY_FLOW.txt
└── venv/                ← Python virtual environment
```

### Why This Structure

- **Clean separation** - Frontend deployed separately from data generation
- **AI Summary via Claude CLI** - Local analysis using `analyzer.py` with `--no-ai` fallback
- **Python scripts for generation** - Scripts run locally/CI to generate `digest.json` before deployment
- **DigestSummary component** - Tabbed display for themes, breaking news, must-read items

## Frontend Architecture

### Stack
- **Astro 5** - Server-side rendering with Vercel adapter
- **Tailwind CSS 3** - Utility-first styling
- **Vanilla JavaScript** - State management (no framework)

### Component Hierarchy

```
Base.astro (Layout)
└── Header.astro
    ├── Fetch Latest button
    └── Theme toggle
└── Controls.astro
    ├── View Switcher (Cards/List/Glance)
    └── Source Filter (All/Reddit/HN)
└── DigestSummary.astro     ← NEW: AI Summary display
    ├── Simple overview tab
    ├── Themes tab
    ├── Breaking tab
    └── Must-Read tab
└── StoryCard.astro / StoryList.astro / StoryGlance.astro
```

### DigestSummary Component

The DigestSummary component displays AI-generated content in a tabbed interface:

| Tab | Content | Source Field |
|-----|---------|-------------|
| Overview | One-line summary | `summary.simple` |
| Themes | Key trends | `summary.themes[]` |
| Breaking | Urgent news | `summary.breaking[]` |
| Must-Read | Essential articles | `summary.mustRead[]` |

### Client-Side Caching

The app implements a hybrid caching strategy for optimal UX:

1. **Page Load** - Check localStorage for today's cached digest
2. **Cache Hit** - Display immediately (no loading skeleton)
3. **Background Refresh** - Fetch fresh data silently, update UI
4. **Cache Miss** - Show loading skeleton, fetch from API

```typescript
// Cache key: 'digest-data'
// Cache structure: { v, d, g, r, h, summary? } (same as API response)
// Validation: Check 'd' field equals today's date (YYYY-MM-DD)
```

**Benefits:**
- Instant page load with cached data
- Always shows latest content (background refresh)
- Works offline with stale-but-valid cache
- No loading skeleton on return visits
- Summary cached with digest data

### State Management

Persisted to `localStorage`:
- `digest-data` - Cached digest with today's date (including AI summary)
- `viewMode` - Current view preference (cards/list/glance)
- `theme` - Dark/light mode preference

## Backend Architecture

### API Endpoint (`src/pages/api/digest.ts`)

Serverless function deployed to Vercel - serves pre-generated digest.json:

1. **Serve static JSON** - Return `public/data/digest.json`
2. **Add metadata** - Attach timestamp to response
3. **CORS headers** - Enable cross-origin requests

### Python Data Generation (scripts/)

```
┌─────────────────┐
│ aggregator.py  │ ← Fetch stories from Reddit + HN
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  analyzer.py    │ ← Generate AI summary (requires Claude CLI)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ generator.py    │ ← Output digest.json + digest.md
└─────────────────┘
```

#### analyzer.py (AI Summary Generation)

Uses Claude CLI to analyze stories and generate structured summaries:

```bash
# Requires Claude CLI installed and authenticated
claude -p --output-format stream-json << 'EOF'
Analyze these AI news stories and provide a structured summary...
EOF
```

**Output:** DigestSummary object with themes, breaking news, must-read items

**Fallback:** Use `--no-ai` flag to skip AI summary generation

### Configuration

```typescript
// API Endpoint
const API_BASE = "/api/digest";
```

```python
# Python Scripts (config.py)
SUBREDDITS = ["ArtificialIntelligence", "LocalLLaMA", "ChatGPT", "MachineLearning"]
HN_API_URL = "https://hacker-news.firebaseio.com/v0"
POST_LIMIT = 10
CLAUDE_MODEL = "sonnet-4-20250514"
```

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        GENERATION FLOW                              │
├─────────────────────────────────────────────────────────────────────┤
│ 1. Run scripts/aggregator.py → Fetch Reddit + HN stories           │
│ 2. Run scripts/analyzer.py   → Generate AI summary (Claude CLI)      │
│ 3. Run scripts/generator.py → Create digest.json + digest.md        │
│ 4. Deploy to Vercel         → Copy digest.json to public/data/      │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                         RUNTIME FLOW                                │
├─────────────────────────────────────────────────────────────────────┤
│ 1. Page Load     → Client checks localStorage for cached digest     │
│ 2. Cache Found   → Display immediately, fetch fresh in background   │
│ 3. Cache Miss    → Show loading, call /api/digest                   │
│ 4. API Request   → Vercel serves pre-generated digest.json          │
│ 5. Response     → Return stories + AI summary                       │
│ 6. Render        → Display stories + summary tabs                    │
│ 7. Persistence  → Save to localStorage for next visit               │
└─────────────────────────────────────────────────────────────────────┘
```

### AI Summary Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                      AI SUMMARY GENERATION                           │
├─────────────────────────────────────────────────────────────────────┤
│ 1. analyzer.py collects top stories from aggregator                  │
│ 2. Formats prompt with story titles, URLs, scores                   │
│ 3. Invokes Claude CLI: claude -p --output-format stream-json         │
│ 4. Parses structured response into DigestSummary format            │
│ 5. Returns {simple, themes, breaking, mustRead, fullBrief}          │
│                                                                         │
│ ERROR HANDLING:                                                       │
│ - Claude CLI not found → Exit with setup instructions               │
│ - Auth failure → Prompt for claude auth                             │
│ - API rate limit → Retry with exponential backoff                   │
│ - Generation timeout → Skip summary, continue without               │
└─────────────────────────────────────────────────────────────────────┘
```

## Deployment to Vercel

### Prerequisites
```bash
# Install Claude CLI (for AI summaries)
# https://docs.anthropic.com/en/docs/claude-code/setup

cd ai-digest-reader
npm install
```

### Generate Digest Locally

```bash
# Generate with AI summary (requires Claude CLI)
python scripts/generator.py

# Generate without AI summary
python scripts/generator.py --no-ai

# Copy to deploy
cp output/digest.json ai-digest-reader/public/data/digest.json
```

### Commands
```bash
# Development
npm run dev

# Build for production
npm run build

# Deploy to Vercel
vercel --prod
```

### Vercel Configuration (`vercel.json`)

```json
{
  "buildCommand": "npm run build",
  "installCommand": "npm install",
  "framework": "astro",
  "outputDirectory": ".vercel/output"
}
```

### Node.js Version

Vercel requires Node 24.x. Set in `package.json`:
```json
{
  "engines": {
    "node": "24.x"
  }
}
```

## PWA Support

- Client-side localStorage caching for offline access
- Theme persistence via localStorage
- View mode persistence
- AI summary cached with digest data
- Responsive viewport meta tags

## Dependencies

| Component | Technology |
|-----------|------------|
| AI Summaries | Claude CLI (Anthropic) |
| Data Fetching | Python requests library |
| Web Framework | Astro 5 |
| Styling | Tailwind CSS 3 |
| Deployment | Vercel |
| Data Format | JSON (schema v2) |
