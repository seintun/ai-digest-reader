# AI Digest Reader

Mobile-first PWA news reader that aggregates AI and tech content from Reddit, Hacker News, and RSS feeds into a clean daily digest with AI-generated summaries.

## Features

- **Multi-source** — Reddit (11 subs), Hacker News, 10 RSS feeds
- **AI summaries** — Daily briefings with themes, breaking news, must-reads, and a full brief (via OpenRouter/Kimi K2)
- **Search** — Real-time full-text search across titles and excerpts
- **Category filters** — All, AI & ML, Tech, Science, World News, Futurology, Startups
- **Source filters** — Reddit, HN, RSS, or All
- **Three view modes** — Cards, list, and glance
- **Bookmarks** — Save stories to a local bookmarks list (localStorage)
- **Bottom navigation** — Mobile-native nav bar (Home / Search / Saved)
- **Dark mode** — System-aware with manual toggle
- **Offline support** — PWA service worker with stale-while-revalidate
- **Responsive** — Mobile-first, works on any screen size

## Quick Start

```bash
# Install dependencies
cd ai-digest-reader
npm install

# Development server
npm run dev

# Production build
npm run build

# Type check
npm run check

# Preview production build
npm run preview
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| Framework | Astro 4 |
| Styling | Tailwind CSS 3 |
| Fonts | @fontsource/inter, @fontsource/newsreader (self-hosted) |
| Language | TypeScript (strict) |
| State | Vanilla JS + custom DOM events |
| Storage | localStorage (bookmarks, theme) |
| PWA | Service worker with dual cache |
| Deployment | Vercel |
| Data | digest.json (schema v3) |

## Project Structure

```
ai-digest-reader/
├── src/
│   ├── pages/
│   │   └── index.astro          ← Main page (thin orchestrator)
│   ├── components/
│   │   ├── Header.astro         ← App header with theme toggle
│   │   ├── Controls.astro       ← Source + view mode tabs
│   │   ├── SearchBar.astro      ← Real-time search input
│   │   ├── CategoryFilter.astro ← Category pill tabs
│   │   ├── BottomNav.astro      ← Mobile bottom navigation
│   │   └── Icons.astro          ← Centralized SVG icon library
│   ├── lib/
│   │   ├── utils.ts             ← Formatting + filtering utilities
│   │   ├── storage.ts           ← localStorage helpers (bookmarks, theme)
│   │   └── window-hooks.ts      ← Typed Window interface augmentation
│   ├── styles/
│   │   └── global.css           ← Base styles, font loading, dark mode
│   └── types.ts                 ← All TypeScript types (Story, Digest, etc.)
├── public/
│   ├── data/digest.json         ← Pre-generated digest (updated by pipeline)
│   ├── sw.js                    ← Service worker
│   ├── manifest.json            ← PWA manifest
│   └── offline.html             ← Offline fallback page
├── docs/                        ← Architecture and developer docs
├── astro.config.mjs
├── tailwind.config.mjs
└── package.json
```

## Component Architecture

Components communicate via custom DOM events — no framework state management needed.

| Event | Dispatched by | Handled in |
|-------|--------------|------------|
| `searchchange` | `SearchBar` | `index.astro` |
| `categorychange` | `CategoryFilter` | `index.astro` |
| `sourcechange` | `Controls` | `index.astro` |
| `navchange` | `BottomNav` | `index.astro` |

### Window hooks

`src/lib/window-hooks.ts` augments the global `Window` interface so cross-component callbacks are fully typed without `(window as any)` casts:

```ts
window.updateSearchInfo(count, query)
window.setNavActive(section)
window.updateBookmarkBadge(count)
```

## Data Flow

```
digest.json
    └── Astro reads at build time (or runtime fetch)
            ├── Reddit stories (digest.r[])
            ├── HN stories (digest.h[])
            └── RSS stories (digest.rs[])
                    ↓
            AppState { stories, searchQuery, category, source, bookmarks }
                    ↓
            filterStories() → filtered[]
                    ↓
            renderCards() / renderList() / renderGlance() / renderBookmarks()
```

## Types

All types are in `src/types.ts`. Key interfaces:

```ts
interface Story {
  i: string;    // id: rd-N, hn-N, rs-N
  t: string;    // title
  u: string;    // article URL
  p?: string;   // discussion permalink
  b?: string;   // body excerpt
  s: number;    // score
  c: number;    // comment count
  a: string;    // author
  cat?: string; // category
}

interface Digest {
  v: 2 | 3;
  d: string;         // date YYYY-MM-DD
  g: string;         // generated ISO timestamp
  r: Story[];        // Reddit
  h: Story[];        // HN
  rs?: Story[];      // RSS (v3+)
  summary?: DigestSummary;
}
```

## PWA / Offline

The service worker (`public/sw.js`) uses two caches:

- **`ai-digest-v2`** — App shell (HTML, CSS, JS, fonts)
- **`digest-data-v1`** — `digest.json` with stale-while-revalidate: serve cached immediately, fetch fresh in background

`public/offline.html` is shown when both the network and cache miss.

## Development

### Adding a new category

1. Add to `CATEGORIES` in `src/types.ts`
2. Add a button in `CategoryFilter.astro`
3. Update `config.py` and `SUBREDDIT_CATEGORIES` / `RSS_FEEDS` in the Python backend

### Adding a new RSS source

Edit `config.py`:

```python
RSS_FEEDS = [
    # ...existing feeds...
    {
        "url": "https://example.com/feed.xml",
        "source": "Example",
        "category": "Tech",
    },
]
```

### Running type checks

```bash
npm run check
```

Uses `astro check` which runs `tsc` over all `.astro` and `.ts` files.

## Documentation

- [Architecture overview](ARCHITECTURE.md)
- [Data schema](DATA_SCHEMA.md)
- [Deployment guide](DEPLOYMENT.md)
- [Troubleshooting](TROUBLESHOOTING.md)
- [Changelog](CHANGELOG.md)
- [Architecture docs](architecture/) — rss-fetcher, ai-summarization, automation, frontend
