# Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                          DATA GENERATION                             │
├─────────────────────────────────────────────────────────────────────┤
│  Python CLI (generate_json.py)                                       │
│  ├── Reddit API (pushshift.io + reddit.com)                        │
│  ├── Hacker News API (firebaseio.com)                              │
│  └── Config (config.py: SUBREDDITS, POST_LIMIT)                    │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ digest.json  │
                    └──────┬───────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                           DEPLOYMENT                                 │
├─────────────────────────────────────────────────────────────────────┤
│  Vercel CDN + Edge Network                                          │
│  ├── Static assets (Astro build output)                             │
│  └── digest.json (regenerated daily via cron/GitHub Actions)      │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                           CLIENT (PWA)                               │
├─────────────────────────────────────────────────────────────────────┤
│  Astro SSG + Tailwind CSS                                          │
│  ├── Theme detection (dark/light mode)                             │
│  ├── View state persistence (localStorage)                        │
│  └── Service worker (offline caching)                             │
└─────────────────────────────────────────────────────────────────────┘
```

## Frontend Architecture

### Stack
- **Astro 4** - Static site generation
- **Tailwind CSS 3** - Utility-first styling
- **Vanilla JavaScript** - State management (no framework)

### Component Hierarchy

```
Base.astro (Layout)
└── Header.astro
    ├── ViewSwitcher.astro
    └── SourceFilter.astro
└── StoryCard.astro / StoryList.astro / StoryGlance.astro
```

### State Management

Custom event-driven state in `src/lib/state.ts`:

```typescript
interface AppState {
  viewMode: 'cards' | 'list' | 'glance';
  source: 'reddit' | 'hn' | 'all';
  stories: Story[];
  loading: boolean;
  error: string | null;
}
```

Persisted to `localStorage`:
- `viewMode` - Current view preference
- `source` - Active filter

## Backend Architecture

### Python CLI (`scripts/generate_json.py`)

1. **Fetch Reddit posts** - Queries configured subreddits via Pushshift and Reddit APIs
2. **Fetch HN posts** - Retrieves top stories from Hacker News Firebase API
3. **Normalize data** - Transforms raw API responses to Story format
4. **Output JSON** - Writes `digest.json` to `public/data/`

### Configuration (`config.py`)

```python
SUBREDDITS = ["ArtificialIntelligence", "LocalLLaMA", "ChatGPT", "MachineLearning"]
HN_API_URL = "https://hacker-news.firebaseio.com/v0"
POST_LIMIT = 10
```

## Data Flow

1. **Generation** - Python script fetches from Reddit + HN APIs
2. **Build** - `digest.json` placed in `public/data/`
3. **Deploy** - Vercel serves static files via CDN
4. **Request** - Client fetches `digest.json` on page load
5. **Render** - Astro components hydrate with story data
6. **Cache** - Service worker caches for offline access

## PWA Support

- Service worker for offline caching
- `apple-mobile-web-app-*` meta tags for iOS add-to-homescreen
- Theme color configuration
- Responsive viewport meta tags
