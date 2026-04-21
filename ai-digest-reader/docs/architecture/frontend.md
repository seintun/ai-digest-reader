# Frontend Architecture

## Stack
- **Astro 4** — static site generator, zero JS framework runtime
- **Tailwind CSS 3.4** — utility-first styling, dark mode via `class` strategy
- **Vanilla TypeScript** — no React/Vue/Svelte; all interactivity via DOM events

## File Structure
```
src/
├── components/         # Astro UI components
│   ├── Header.astro    # Sticky header, dark mode toggle
│   ├── Controls.astro  # View mode + source filter
│   ├── SearchBar.astro # Real-time search input
│   ├── CategoryFilter.astro  # Horizontal category pill tabs
│   ├── BottomNav.astro # Mobile-only bottom navigation
│   └── Icons.astro     # Centralized SVG icon component
├── lib/                # Pure TypeScript utilities
│   ├── ranking.ts      # Story ranking algorithm
│   ├── utils.ts        # escapeHtml, safeExternalUrl, formatCount, etc.
│   ├── storage.ts      # localStorage abstraction (bookmarks, theme)
│   └── window-hooks.ts # Window interface augmentation for cross-component hooks
├── pages/
│   └── index.astro     # Single page: app shell + all rendering logic
├── types.ts            # TypeScript interfaces (Story, Digest, Source, Category, etc.)
└── styles/
    └── global.css      # Font imports, Tailwind base layer
```

## Component Communication
Components communicate via **custom DOM events** dispatched on `document`:
| Event | Payload | Dispatched by | Handled by |
|-------|---------|---------------|------------|
| `searchchange` | `{ query: string }` | SearchBar | index.astro |
| `categorychange` | `{ category: string }` | CategoryFilter | index.astro |
| `sourcechange` | `{ source: string }` | Controls | index.astro |
| `viewchange` | `{ mode: string }` | Controls | index.astro |
| `navchange` | `{ nav: string }` | BottomNav | index.astro |

Components that need to call back into index.astro use typed window hooks declared in `lib/window-hooks.ts`.

## Data Flow
```
/data/digest.json (static)
    ↓ fetch()
index.astro state: { stories, filteredStories, source, category, searchQuery, bookmarks }
    ↓ filterStories() + rankStories()
state.filteredStories
    ↓ renderStories() / renderBookmarks()
DOM innerHTML update
```

## Performance

### Code Splitting
Vite auto-splits JS chunks (no `manualChunks` override). The current single bundle is ~40KB gzipped.

### Fonts
Inter and Newsreader are self-hosted via `@fontsource` — no render-blocking Google Fonts request. DM Serif Display and IBM Plex Mono load from Google Fonts CDN with `display=swap`.

### Service Worker (`public/sw.js`)
- **Shell assets** (HTML, manifest, offline.html): cache-first, precached on install
- **digest.json**: stale-while-revalidate — instant load from cache, background refresh
- **Other assets**: cache-first with network fallback
- **Offline fallback**: `/offline.html` served when network unavailable

### Bundle Size (target)
- JS bundle: < 50KB gzip
- Fonts: served locally, no network waterfall

## Adding a New Source
1. Add fetcher in Python backend (`fetchers/`)
2. Add new prefix (e.g. `gh-`) to digest.json in `digest.py`
3. Update `Story.i` prefix handling in `src/lib/utils.ts` (`getSourceCounts`, `getDiscussionUrl`)
4. Add source button to `Controls.astro`
5. Update `Source` type in `src/types.ts`
