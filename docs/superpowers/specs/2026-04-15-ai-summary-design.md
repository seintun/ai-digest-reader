# AI Summary Feature for Daily Digest

**Date:** 2026-04-15  
**Status:** Draft  
**Version:** 1.0

---

## Overview

Add AI-powered daily digest summary feature with tabbed display (Simple | Structured | Full Brief) shown at the top of the news cards/list. The AI analysis runs during `digest.py` execution via Claude CLI subprocess.

---

## Goals

1. Generate concise, AI-powered summaries of daily AI news
2. Display summaries in mobile-friendly tabbed interface
3. Provide three viewing modes: Simple TL;DR, Structured breakdown, Full Brief
4. Graceful fallback when AI analysis is unavailable
5. Use Claude CLI (OAuth-based, no API keys) for analysis

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  digest.py                                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐   │
│  │   fetchers  │───▶│  analyzer   │───▶│  formatter  │   │
│  │ (reddit/hn) │    │ (claude CLI)│    │ (JSON+MD)   │   │
│  └─────────────┘    └─────────────┘    └─────────────┘   │
│         │                                       │          │
│         └───────────────────────────────────────┘          │
│                    output/digest.json                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  ai-digest-reader (Frontend)                                │
│  ┌─────────────────┐    ┌─────────────────────────────┐    │
│  │ DigestSummary   │    │ Stories (cards/list/glance) │    │
│  │ .astro          │    │                             │    │
│  │ [Tabbed UI]    │    │                             │    │
│  └─────────────────┘    └─────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Format

### JSON Output (Version 2)

```json
{
  "v": 2,
  "d": "2026-04-15",
  "g": "2026-04-15T08:39:14",
  "r": [
    {
      "i": "rd-0",
      "t": "Story title",
      "u": "https://...",
      "s": 387,
      "c": 175,
      "a": "username"
    }
  ],
  "h": [
    {
      "i": "hn-0",
      "t": "Story title",
      "u": "https://...",
      "s": 67,
      "c": 44,
      "a": "username"
    }
  ],
  "summary": {
    "simple": "2-3 sentence TL;DR covering the main themes",
    "structured": {
      "themes": ["Theme 1", "Theme 2", "Theme 3"],
      "breaking": "One line on the most significant news",
      "mustRead": [
        {
          "id": "rd-19",
          "t": "Story title",
          "url": "https://...",
          "reason": "Why this is must read"
        },
        {
          "id": "rd-10",
          "t": "Story title",
          "url": "https://...",
          "reason": "Why this is must read"
        },
        {
          "id": "hn-3",
          "t": "Story title",
          "url": "https://...",
          "reason": "Why this is must read"
        }
      ]
    },
    "fullBrief": "## Full Brief\n\nMarkdown content..."
  }
}
```

### Fallback Behavior

If AI analysis fails, `summary` field is omitted entirely:

```json
{
  "v": 2,
  "d": "2026-04-15",
  "g": "2026-04-15T08:39:14",
  "r": [...],
  "h": [...]
}
```

---

## Backend Implementation

### New File: `analyzer.py`

**Location:** `/Users/seintun/code/dailydigest/analyzer.py`

**Purpose:** Handle Claude CLI subprocess for AI analysis

**Functions:**

```python
import subprocess
import json
from typing import Dict, Any, List, Optional

def generate_summary(reddit_posts: List[Dict], hn_posts: List[Dict]) -> Optional[Dict[str, Any]]:
    """
    Calls claude CLI with all stories, returns structured JSON.
    Returns None if analysis fails.
    """
    prompt = _build_prompt(reddit_posts, hn_posts)
    
    try:
        result = subprocess.run(
            ["claude", "--print", prompt],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            print(f"Claude CLI error: {result.stderr}")
            return None
            
        return _parse_claude_response(result.stdout)
        
    except FileNotFoundError:
        print("Warning: claude CLI not found. Install with: npm install -g @anthropic-ai/claude")
        return None
    except subprocess.TimeoutExpired:
        print("Warning: Claude CLI timed out after 60s")
        return None
    except Exception as e:
        print(f"Warning: Claude analysis failed: {e}")
        return None

def _build_prompt(reddit_posts: List[Dict], hn_posts: List[Dict]) -> str:
    """Build prompt with formatted stories."""
    lines = ["Analyze these AI news stories and generate a structured summary in JSON format.\n"]
    
    lines.append("## Reddit Stories")
    for i, post in enumerate(reddit_posts):
        lines.append(f"- [{post['i']}] {post['t']} (score: {post['s']}, comments: {post['c']})")
    
    lines.append("\n## Hacker News Stories")
    for i, post in enumerate(hn_posts):
        lines.append(f"- [{post['i']}] {post['t']} (score: {post['s']}, comments: {post['c']})")
    
    lines.append("""
Generate JSON with exactly this structure:
{
  "simple": "2-3 sentence TL;DR covering the main themes",
  "structured": {
    "themes": ["Theme 1", "Theme 2", "Theme 3"],
    "breaking": "One line on the most significant news",
    "mustRead": [
      {"id": "story-id", "t": "Story title", "url": "story-url", "reason": "Why this is must read"}
    ]
  },
  "fullBrief": "## Full Brief\n\nMarkdown content with sections..."
}

Rules:
- mustRead must have exactly 3 items
- Include the story URL for linking
- Keep reasons to 1 sentence
- fullBrief should be 3-5 paragraphs in markdown
- Output ONLY valid JSON, no markdown code blocks or explanation
""")
    
    return "\n".join(lines)

def _parse_claude_response(response: str) -> Optional[Dict[str, Any]]:
    """Parse JSON from Claude output."""
    text = response.strip()
    
    # Remove markdown code blocks if present
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.strip()
    
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"Warning: Failed to parse Claude JSON: {e}")
        return None
```

### Modified File: `digest.py`

**Changes:**
1. Import analyzer
2. Call `generate_summary()` after fetching stories
3. Include summary in digest JSON
4. Add try/catch with graceful fallback

```python
#!/usr/bin/env python3
"""AI News Digest Aggregator - Main CLI."""
import argparse
from datetime import date, datetime
from pathlib import Path
import json

from config import SUBREDDITS, POST_LIMIT, DATE_FORMAT
from fetchers import fetch_reddit_posts, fetch_hn_posts
from formatter import format_digest

# New import
try:
    from analyzer import generate_summary
except ImportError:
    generate_summary = None


def main():
    parser = argparse.ArgumentParser(description="AI News Digest Generator")
    parser.add_argument("--limit", type=int, default=POST_LIMIT, help="Posts per source")
    parser.add_argument("--output-dir", type=str, help="Output directory (default: output/YYYY-MM-DD)")
    parser.add_argument("--subreddits", nargs="*", help="Specific subreddits to fetch")
    parser.add_argument("--no-ai", action="store_true", help="Skip AI summary generation")
    args = parser.parse_args()
    
    # ... existing fetch code ...
    
    # Generate AI summary
    summary = None
    if generate_summary and not args.no_ai:
        print("Generating AI summary...")
        summary = generate_summary(all_reddit_posts, hn_posts)
        if summary:
            print("AI summary generated successfully")
        else:
            print("AI summary unavailable, continuing without it")
    
    # Build digest data
    digest_date = date.today().strftime(DATE_FORMAT)
    digest_time = datetime.now().strftime("%H%M%S")
    
    digest = {
        "v": 2,
        "d": digest_date,
        "g": datetime.now().isoformat(),
        "r": all_reddit_posts,
        "h": hn_posts,
    }
    
    if summary:
        digest["summary"] = summary
    
    # Output markdown (existing behavior)
    content = format_digest(all_reddit_posts, hn_posts, digest_date)
    print("\n" + content)
    
    # Save JSON with summary
    output_dir = Path(args.output_dir) if args.output_dir else Path("output") / digest_date
    output_dir.mkdir(parents=True, exist_ok=True)
    
    json_path = output_dir / "digest.json"
    with open(json_path, "w") as f:
        json.dump(digest, f, indent=2)
    print(f"Saved JSON to {json_path}")
    
    # Save markdown (existing behavior)
    filename = f"digest-{digest_date}-{digest_time}.md"
    output_path = output_dir / filename
    # ... existing timestamp handling ...
    output_path.write_text(content)
    print(f"Saved markdown to {output_path}")


if __name__ == "__main__":
    main()
```

---

## Frontend Implementation

### Modified File: `src/types.ts`

```typescript
export interface MustReadItem {
  id: string;
  t: string;
  url: string;
  reason: string;
}

export interface DigestSummary {
  simple: string;
  structured: {
    themes: string[];
    breaking: string;
    mustRead: MustReadItem[];
  };
  fullBrief: string;
}

export interface Digest {
  v: 1 | 2;
  d: string;
  g: string;
  r: Story[];
  h: Story[];
  summary?: DigestSummary;  // Optional - only in v2
}
```

### New File: `src/components/DigestSummary.astro`

**Location:** `/Users/seintun/code/dailydigest/ai-digest-reader/src/components/DigestSummary.astro`

**Purpose:** Tabbed AI summary display component

```astro
---
import type { DigestSummary } from '../types';

interface Props {
  summary: DigestSummary;
  stories: Array<{ i: string; u: string }>;
}

const { summary, stories } = Astro.props;

function getStoryUrl(id: string): string {
  const story = stories.find(s => s.i === id);
  return story?.u || '#';
}
---

<div class="digest-summary backdrop-blur-md bg-white/80 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/50 rounded-2xl p-4 mb-4">
  <div class="flex items-center justify-between mb-3">
    <div class="flex items-center gap-2">
      <svg class="w-5 h-5 text-primary-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
      </svg>
      <span class="font-semibold text-sm text-slate-700 dark:text-slate-200">AI Summary</span>
    </div>
    
    <div class="relative">
      <button 
        id="summary-tab-toggle" 
        class="flex items-center gap-1 text-sm text-primary-600 dark:text-primary-400 font-medium cursor-pointer px-2 py-1 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors duration-200"
      >
        <span id="current-tab-label">Simple</span>
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      
      <div id="summary-tabs-dropdown" class="hidden absolute right-0 mt-1 w-36 bg-white dark:bg-slate-800 rounded-lg shadow-lg border border-slate-200 dark:border-slate-700 z-50">
        <button data-tab="simple" class="tab-btn w-full text-left px-3 py-2 text-sm hover:bg-slate-100 dark:hover:bg-slate-700 cursor-pointer rounded-t-lg transition-colors duration-150">Simple</button>
        <button data-tab="structured" class="tab-btn w-full text-left px-3 py-2 text-sm hover:bg-slate-100 dark:hover:bg-slate-700 cursor-pointer transition-colors duration-150">Structured</button>
        <button data-tab="full" class="tab-btn w-full text-left px-3 py-2 text-sm hover:bg-slate-100 dark:hover:bg-slate-700 cursor-pointer rounded-b-lg transition-colors duration-150">Full Brief</button>
      </div>
    </div>
  </div>
  
  <!-- Simple Tab -->
  <div id="summary-simple" class="tab-content">
    <p class="text-slate-600 dark:text-slate-300 text-sm leading-relaxed">{summary.simple}</p>
  </div>
  
  <!-- Structured Tab -->
  <div id="summary-structured" class="tab-content hidden">
    <div class="space-y-4">
      <!-- Themes -->
      <div>
        <h4 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">Today's Themes</h4>
        <div class="flex flex-wrap gap-2">
          {summary.structured.themes.map(theme => (
            <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300">
              {theme}
            </span>
          ))}
        </div>
      </div>
      
      <!-- Breaking -->
      {summary.structured.breaking && (
        <div>
          <h4 class="text-xs font-semibold text-red-600 dark:text-red-400 uppercase tracking-wider mb-2 flex items-center gap-1">
            <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            Breaking
          </h4>
          <p class="text-sm text-slate-700 dark:text-slate-300">{summary.structured.breaking}</p>
        </div>
      )}
      
      <!-- Must Read -->
      <div>
        <h4 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">Must Read</h4>
        <div class="space-y-2">
          {summary.structured.mustRead.map((item, idx) => (
            <a 
              href={getStoryUrl(item.id)} 
              target="_blank" 
              rel="noopener noreferrer"
              class="flex items-start gap-2 group cursor-pointer"
            >
              <span class="flex-shrink-0 w-5 h-5 rounded-full bg-primary-100 dark:bg-primary-900/40 text-primary-600 dark:text-primary-400 text-xs font-semibold flex items-center justify-center">
                {idx + 1}
              </span>
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-slate-800 dark:text-slate-200 group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors duration-150 truncate">
                  {item.t}
                </p>
                <p class="text-xs text-slate-500 dark:text-slate-400">{item.reason}</p>
              </div>
              <svg class="flex-shrink-0 w-4 h-4 text-slate-400 group-hover:text-primary-500 transition-colors duration-150 mt-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </a>
          ))}
        </div>
      </div>
    </div>
  </div>
  
  <!-- Full Brief Tab -->
  <div id="summary-full" class="tab-content hidden">
    <div class="digest-prose text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
      <Fragment set:html={summary.fullBrief.replace(/\n/g, '<br/>').replace(/##\s+(.+)/g, '<h3 class="text-base font-semibold text-slate-800 dark:text-slate-100 mt-4 mb-2">$1</h3>').replace(/###\s+(.+)/g, '<h4 class="text-sm font-semibold text-slate-700 dark:text-slate-200 mt-3 mb-1">$1</h4>').replace(/-\s+(.+)/g, '<li class="ml-4">$1</li>')} />
    </div>
  </div>
</div>

<style>
  .tab-btn.active {
    background-color: rgb(239 246 255 / 0.8);
    color: rgb(37 99 235);
  }
  
  :global(.dark) .tab-btn.active {
    background-color: rgb(30 58 138 / 0.3);
    color: rgb(147 197 253);
  }
  
  .digest-prose h3:first-child {
    margin-top: 0;
  }
</style>

<script>
  const toggle = document.getElementById('summary-tab-toggle');
  const dropdown = document.getElementById('summary-tabs-dropdown');
  const tabButtons = document.querySelectorAll('.tab-btn');
  const tabContents = document.querySelectorAll('.tab-content');
  const currentLabel = document.getElementById('current-tab-label');
  
  const tabLabels: Record<string, string> = {
    simple: 'Simple',
    structured: 'Structured',
    full: 'Full Brief'
  };
  
  let activeTab = 'simple';
  
  toggle?.addEventListener('click', (e) => {
    e.stopPropagation();
    dropdown?.classList.toggle('hidden');
  });
  
  document.addEventListener('click', () => {
    dropdown?.classList.add('hidden');
  });
  
  tabButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const tab = btn.getAttribute('data-tab');
      if (!tab) return;
      
      activeTab = tab;
      
      // Update button states
      tabButtons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      
      // Update label
      if (currentLabel) {
        currentLabel.textContent = tabLabels[tab] || tab;
      }
      
      // Show/hide content
      tabContents.forEach(content => {
        const id = content.id.replace('summary-', '');
        content.classList.toggle('hidden', id !== tab);
      });
      
      // Close dropdown
      dropdown?.classList.add('hidden');
    });
  });
  
  // Set initial active state
  tabButtons.forEach(btn => {
    if (btn.getAttribute('data-tab') === activeTab) {
      btn.classList.add('active');
    }
  });
</script>
```

### Modified File: `src/pages/index.astro`

**Changes:**
1. Import DigestSummary component
2. Fetch digest data with summary
3. Conditionally render DigestSummary only if summary exists

```astro
---
import Base from '../layouts/Base.astro';
import Header from '../components/Header.astro';
import Controls from '../components/Controls.astro';
import DigestSummary from '../components/DigestSummary.astro';
import type { Story, Digest, ViewMode, Source } from '../types';

interface Props {}
const { } = Astro.props;
---

<Base title="AI Digest - Your Daily AI News">
  <Header />

  <main class="max-w-4xl mx-auto px-2 sm:px-3 py-2 sm:py-3">
    <div id="controls-container" class="mb-3">
      <Controls />
    </div>

    <!-- AI Summary Section -->
    <div id="summary-container" class="hidden">
      <DigestSummary id="digest-summary" />
    </div>

    <!-- ... existing pull-refresh-hint, loading, error, stories containers ... -->
  </main>
</Base>

<script>
  import type { Digest, Story, ViewMode, Source, DigestSummary } from '../types';
  import DigestSummaryComponent from '../components/DigestSummary.astro';
  // ...

  interface AppState {
    stories: Story[];
    filteredStories: Story[];
    summary: DigestSummary | null;
    viewMode: ViewMode;
    source: Source;
    isLoading: boolean;
    error: string | null;
  }

  // ...

  async function fetchDigest() {
    showLoading();
    try {
      const response = await fetch('/data/digest.json');
      if (!response.ok) {
        throw new Error(`Failed to fetch digest: ${response.status}`);
      }
      const data: Digest = await response.json();

      state.stories = [...data.r, ...data.h];
      state.summary = data.summary || null;  // Handle missing summary
      state.filteredStories = filterStories(state.stories, state.source);

      // Show/hide summary section
      const summaryContainer = document.getElementById('summary-container');
      if (summaryContainer) {
        if (state.summary) {
          summaryContainer.classList.remove('hidden');
          // Pass data to DigestSummary component via DOM
          const summaryEl = document.getElementById('digest-summary');
          if (summaryEl) {
            summaryEl.dataset.summary = JSON.stringify(state.summary);
            summaryEl.dataset.stories = JSON.stringify(state.stories);
          }
        } else {
          summaryContainer.classList.add('hidden');
        }
      }

      updateSourceFilter();
      renderStories();
      hideLoading();
    } catch (error) {
      console.error('Error fetching digest:', error);
      showError(error instanceof Error ? error.message : 'Failed to load stories');
    }
  }
  
  // ... rest of existing code ...
</script>
```

---

## Styling Guidelines

### Color Palette

| Element | Light Mode | Dark Mode |
|---------|------------|-----------|
| Summary Card BG | `bg-white/80` | `bg-slate-800/60` |
| Card Border | `border-slate-200` | `border-slate-700/50` |
| Primary Text | `text-slate-800` | `text-slate-100` |
| Muted Text | `text-slate-600` | `text-slate-400` |
| Theme Pills | `bg-slate-100` | `bg-slate-700` |
| Breaking Badge | `text-red-600` | `text-red-400` |
| Must-Read Numbers | `bg-primary-100 text-primary-600` | `bg-primary-900/40 text-primary-400` |
| Links on Hover | `text-primary-600` | `text-primary-400` |

### Spacing

- Card padding: `p-4`
- Card margin-bottom: `mb-4`
- Section gap: `gap-2` to `gap-4`
- Pill padding: `px-2.5 py-1`

### Typography

- Card title: `text-sm font-medium`
- Section headers: `text-xs font-semibold uppercase tracking-wider`
- Body text: `text-sm leading-relaxed`
- Must-read titles: `text-sm font-medium`

---

## Error Handling

### Backend Fallbacks

| Failure Mode | Behavior |
|--------------|----------|
| `claude` CLI not installed | Print warning, save digest without summary |
| Claude timeout (>60s) | Print warning, save digest without summary |
| Claude returns non-JSON | Print warning, save digest without summary |
| Network/API error | Print warning, save digest without summary |

### Frontend Fallbacks

| Condition | Behavior |
|-----------|----------|
| `summary` field missing | Hide DigestSummary component entirely |
| Invalid summary data | Hide DigestSummary component entirely |
| Tab content empty | Show placeholder text |

---

## Testing Checklist

### Backend
- [ ] Claude CLI installed and authenticated
- [ ] `python digest.py` generates summary
- [ ] `python digest.py --no-ai` skips summary
- [ ] Digest JSON includes `summary` field when successful
- [ ] Digest JSON omits `summary` field when AI fails
- [ ] Must-read items link to correct stories

### Frontend
- [ ] Summary section hidden when no `summary` data
- [ ] Summary section visible when `summary` data exists
- [ ] Tab switching works (Simple ↔ Structured ↔ Full Brief)
- [ ] Mobile layout displays correctly
- [ ] Dark mode displays correctly
- [ ] Must-read items are clickable links
- [ ] Loading state doesn't show summary
- [ ] Error state doesn't show summary

### Visual
- [ ] Glass card styling matches existing design
- [ ] Tab dropdown has proper z-index
- [ ] Smooth transitions on hover/tab switch
- [ ] Proper contrast in light and dark modes
- [ ] Responsive at 375px (mobile)

---

## Files to Create/Modify

### Create
- `analyzer.py` - Claude CLI integration module

### Modify
- `digest.py` - Add AI summary generation, JSON output
- `ai-digest-reader/src/types.ts` - Add DigestSummary types
- `ai-digest-reader/src/components/DigestSummary.astro` - New tabbed summary component
- `ai-digest-reader/src/pages/index.astro` - Include summary, conditional rendering

### No Changes Needed
- `formatter.py` - Continues to generate markdown
- `fetchers/` - No changes required
- `config.py` - No changes required

---

## Dependencies

### Backend
- Python 3.8+
- `requests` (existing)
- `claude` CLI (must be installed separately)

### Frontend
- Astro (existing)
- Tailwind CSS (existing)
- No new npm packages required

---

## Notes

1. **Claude CLI Installation:** Users must install Claude CLI (`npm install -g @anthropic-ai/claude`) and authenticate with `claude auth login` before using this feature.

2. **Rate Limits:** Claude has usage limits on free tier. Large digests may need batching.

3. **Version Compatibility:** Frontend checks for `v: 2` in digest JSON. Backwards compatible with v1 (no summary).

4. **Markdown Rendering:** Full Brief tab uses simple string replacement for markdown. For production, consider a proper markdown parser.
