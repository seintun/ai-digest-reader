# Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                          DATA SOURCES                                │
├─────────────────────────────────────────────────────────────────────┤
│  1. Reddit API (pushshift.io + reddit.com)                          │
│  2. Hacker News API (firebaseio.com)                               │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        DEPLOYMENT                                   │
├─────────────────────────────────────────────────────────────────────┤
│  Vercel (Serverless Functions + CDN)                               │
│  ├── /api/digest → Live data on each request                      │
│  └── Static assets → CDN edge network                             │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                           CLIENT (PWA)                              │
├─────────────────────────────────────────────────────────────────────┤
│  Astro SSR + Tailwind CSS                                          │
│  ├── Client-side caching (localStorage)                            │
│  ├── Theme detection (dark/light mode)                            │
│  └── View state persistence                                        │
└─────────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
dailydigest/
├── ai-digest-reader/     ← Vercel deployment target (THIS IS DEPLOYED)
│   ├── src/
│   │   └── pages/api/   ← /api/digest serverless endpoint
│   ├── public/
│   ├── package.json
│   ├── astro.config.mjs
│   └── vercel.json
├── scripts/              ← Python CLI (local/CI, NOT deployed to Vercel)
│   ├── generate_json.py
│   └── config.py
├── docs/
│   ├── ARCHITECTURE.md
│   └── README.md
└── venv/                ← Python virtual environment
```

### Why This Structure

- **Clean separation** - Frontend deployed separately from data generation
- **Live API on Vercel** - `/api/digest` runs as serverless function, fetches live data on each request
- **Python scripts optional** - Data can be generated live via API; scripts are for backup/offline generation

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
└── StoryCard.astro / StoryList.astro / StoryGlance.astro
```

### Client-Side Caching

The app implements a hybrid caching strategy for optimal UX:

1. **Page Load** - Check localStorage for today's cached digest
2. **Cache Hit** - Display immediately (no loading skeleton)
3. **Background Refresh** - Fetch fresh data silently, update UI
4. **Cache Miss** - Show loading skeleton, fetch from API

```typescript
// Cache key: 'digest-data'
// Cache structure: { v, d, g, r, h } (same as API response)
// Validation: Check 'd' field equals today's date (YYYY-MM-DD)
```

**Benefits:**
- Instant page load with cached data
- Always shows latest content (background refresh)
- Works offline with stale-but-valid cache
- No loading skeleton on return visits

### State Management

Persisted to `localStorage`:
- `digest-data` - Cached digest with today's date
- `viewMode` - Current view preference (cards/list/glance)
- `theme` - Dark/light mode preference

## Backend Architecture

### API Endpoint (`src/pages/api/digest.ts`)

Serverless function deployed to Vercel - fetches live data on each request:

1. **Fetch Reddit posts** - Queries configured subreddits via Pushshift and Reddit APIs
2. **Fetch HN posts** - Retrieves top stories from Hacker News Firebase API
3. **Normalize data** - Transforms raw API responses to Story format
4. **Return JSON** - Serves live data on each request

### Configuration

```typescript
const SUBREDDITS = ["ArtificialIntelligence", "LocalLLaMA", "ChatGPT", "MachineLearning"];
const HN_API_URL = "https://hacker-news.firebaseio.com/v0";
const POST_LIMIT = 10;
```

## Data Flow

1. **Page Load** - Client checks localStorage for cached digest
2. **Cache Found** - Display immediately, fetch fresh in background
3. **Cache Miss** - Show loading, call `/api/digest`
4. **API Request** - Vercel serverless function fetches from Reddit + HN
5. **Response** - Return normalized stories, cache in localStorage
6. **Render** - Display stories in selected view mode
7. **Persistence** - Save to localStorage for next visit

## Deployment to Vercel

### Prerequisites
```bash
cd ai-digest-reader
npm install
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
- Responsive viewport meta tags