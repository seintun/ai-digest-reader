# Data Schema

> The current production schema is **v4**. The Python single source of truth is
> `schema.py`; the TypeScript mirror lives in `src/types.ts`. v1/v2 are retained
> below for historical reference and backward compatibility.

## Digest Structure (v4)

```typescript
interface Digest {
  v: 2 | 3 | 4;          // Schema version (current: 4)
  d: string;             // Digest date (YYYY-MM-DD)
  g: string;             // Generated timestamp (ISO 8601)
  r: Story[];            // Reddit stories
  h: Story[];            // Hacker News stories
  rs?: Story[];          // RSS stories (v3+)
  metrics?: Metrics;     // Run metrics (v4)
  summary?: DigestSummary; // AI-generated summary + optional analysis
}
```

## Story Structure

```typescript
interface Story {
  i: string;      // ID (format: "rd-{n}", "hn-{n}", or "rs-{n}")
  t: string;      // Title
  u: string;      // Article URL
  p?: string;     // Discussion permalink
  b?: string;     // Body excerpt (~280 chars)
  s: number;      // Score (upvotes on Reddit, points on HN; 0 for RSS)
  c: number;      // Comment count
  a?: string;     // Author
  sn?: string;    // Source name (e.g. "r/LocalLLaMA")
  cat?: string;   // Category
  ts?: number;    // Created timestamp (unix seconds)
  rank?: number;  // Importance score (0-100)
  content_available?: boolean;       // Whether article content was scraped
  content_quality?: number;          // Substance score (1-10; title-heuristic fallback)
  excerpt?: string;                  // First ~400 chars of scraped content
  discussion_context?: Comment[];    // (HN only) Top comments, when enrichment is on
}

interface Comment {
  author: string;
  text: string;   // HTML-stripped, truncated to ~500 chars
  depth: number;  // 0 = top-level, 1 = reply
}
```

## DigestSummary Structure (v2+)

```typescript
interface DigestSummary {
  schema_version: string;  // Always "2" for the summary block
  simple: string;          // 2-3 sentence TL;DR
  structured: Structured;  // Themes, breaking headline, must-reads
  fullBrief: FullBrief;    // Structured long-form briefing
  analysis?: DigestAnalysis; // Stage-3 devil's-advocate analysis (optional)
}

interface Structured {
  themes: string[];        // Key themes/trends (exactly 3)
  breaking: string;        // Single breaking headline sentence
  mustRead: MustReadItem[]; // Essential reading (exactly 3)
}

interface FullBrief {
  intro: string;                // Opening paragraph
  sections: FullBriefSection[]; // Body sections (2-4)
  closing: string;              // One-sentence takeaway
}

interface FullBriefSection {
  heading: string;  // Section title
  body: string;     // Paragraph text
}

interface DigestAnalysis {
  implications: string[];   // 1-3: what this means (engineers / industry)
  skeptic_take: string;     // Strongest counter-argument
  confidence: 'high' | 'medium' | 'low';
  evidence_basis: string[]; // 1-4: which claims are verified vs title-only
}
```

## MustReadItem Structure

```typescript
interface MustReadItem {
  id: string;      // Story ID (e.g. "rd-0", "hn-3")
  title: string;   // Article title
  url: string;     // Article URL
  reason: string;  // Why this is essential reading
}
```

## Metrics Structure (v4)

```typescript
interface Metrics {
  runtime: { total_seconds: number; within_budget: boolean; /* per-stage seconds */ };
  scraping: {
    candidate_urls: number;
    success_rate: number;      // cache-inclusive
    cache_hit_rate: number;
    extractor_breakdown: {     // which extractor won each URL + why others failed
      [extractor: string]: number; // defuddle/trafilatura/readability/lxml/metadata/jina/archive/cache/none
      failure_reasons: { [stageReason: string]: number }; // e.g. "defuddle:no_output": 6
    };
  };
  ranking: { total_posts: number; llm_quality_used: boolean };
  summary: { source: string; generated: boolean };
  analysis?: { source: string; generated: boolean; confidence?: string };
  quality: {
    total_stories: number;
    stories_with_content: number;
    content_coverage_pct: number;  // % of ALL stories with content (informational)
    scrape_success_rate: number;   // % of attempted URLs that returned content (gate signal)
    scrape_candidate_urls: number;
    source_counts: { reddit: number; hackernews: number; rss: number };
    analysis_generated: boolean;
  };
  cost: { session_model_usd: number; within_budget: boolean; /* ... */ };
  degradation: {
    scraping_fallback_used: boolean;
    ranking_fallback_used: boolean;
    summary_fallback_used: boolean;
    no_summary_fallback_used: boolean;
  };
}
```

## Field Specifications

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `v` | number | Schema version (`1` or `2`) | `2` |
| `d` | string | Digest date in YYYY-MM-DD format | `"2026-04-15"` |
| `g` | string | ISO 8601 timestamp of generation | `"2026-04-15T08:30:00+00:00"` |
| `r` | Story[] | Array of Reddit stories | `[{...}, {...}]` |
| `h` | Story[] | Array of Hacker News stories | `[{...}, {...}]` |
| `summary` | DigestSummary? | AI-generated summary (v2) | `{simple, themes, ...}` |

### Story Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `i` | string | Unique identifier with source prefix | `"rd-0"`, `"hn-5"` |
| `t` | string | Post/article title | `"GPT-5 released today"` |
| `u` | string | Direct URL to content | `"https://openai.com/blog/..."` |
| `s` | number | Score (upvotes on Reddit, points on HN) | `1523` |
| `c` | number | Number of comments | `342` |
| `a` | string | Author/username | `"sama"` |

### DigestSummary Fields (v2)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `simple` | string | 2-3 sentence TL;DR | `"AI advances dominated..."` |
| `structured.themes` | string[] | Key themes (exactly 3) | `["Multimodal AI", "Open Source", "Policy"]` |
| `structured.breaking` | string | Single breaking headline sentence | `"Anthropic releases Claude 4"` |
| `structured.mustRead` | MustReadItem[] | Essential reading (exactly 3) | `[{id, title, url, reason}]` |
| `fullBrief` | FullBrief | Structured long-form briefing (intro/sections/closing) | `{intro, sections, closing}` |
| `analysis` | DigestAnalysis? | Stage-3 devil's-advocate analysis (optional) | `{implications, skeptic_take, confidence, evidence_basis}` |

### MustReadItem Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `id` | string | Story ID (e.g. `"rd-0"`, `"hn-3"`) | `"hn-3"` |
| `title` | string | Article title | `"Claude 4 Technical Report"` |
| `url` | string | Direct URL to article | `"https://anthropic.com/..."` |
| `reason` | string | Why this is must-read | `"First detailed look at..."` |

## Example Data

### Version 1 (Basic)

```json
{
  "v": 1,
  "d": "2026-04-15",
  "g": "2026-04-15T08:30:00+00:00",
  "r": [
    {
      "i": "rd-0",
      "t": "Anthropic releases Claude 4 with 1M context window",
      "u": "https://anthropic.com/news/claude-4",
      "s": 4521,
      "c": 892,
      "a": "user123"
    }
  ],
  "h": [
    {
      "i": "hn-0",
      "t": "Show HN: Open source LLM trained for $100",
      "u": "https://github.com/example/llm",
      "s": 2103,
      "c": 445,
      "a": "developer"
    }
  ]
}
```

### Version 2 (With AI Summary)

```json
{
  "v": 2,
  "d": "2026-04-15",
  "g": "2026-04-15T08:30:00+00:00",
  "r": [
    {
      "i": "rd-0",
      "t": "Anthropic releases Claude 4 with 1M context window",
      "u": "https://anthropic.com/news/claude-4",
      "s": 4521,
      "c": 892,
      "a": "user123"
    }
  ],
  "h": [
    {
      "i": "hn-0",
      "t": "Show HN: Open source LLM trained for $100",
      "u": "https://github.com/example/llm",
      "s": 2103,
      "c": 445,
      "a": "developer"
    }
  ],
  "summary": {
    "simple": "Major AI releases dominated today's feed with Claude 4 and Gemini Ultra 2 announcements.",
    "themes": [
      "Multimodal AI capabilities",
      "Extended context windows",
      "Open source alternatives",
      "Enterprise AI deployment"
    ],
    "breaking": [
      "Claude 4: 1M token context window now available",
      "Google announces Gemini Ultra 2 with native tool use"
    ],
    "mustRead": [
      {
        "title": "Claude 4 Technical Report",
        "url": "https://anthropic.com/research/claude-4",
        "source": "reddit",
        "reason": "Comprehensive technical deep-dive into the architecture"
      },
      {
        "title": "Training a Production LLM for $500",
        "url": "https://news.ycombinator.com/item?id=123456",
        "source": "hn",
        "reason": "Practical guide from someone who actually did it"
      }
    ],
    "fullBrief": "Today's AI news was dominated by major model releases and competitive developments in the open source space. Anthropic's Claude 4 launch introduced a groundbreaking 1M token context window, while Google's Gemini Ultra 2 added native tool use capabilities. The Hacker News community showed strong interest in cost-effective training methods, with several threads discussing sub-$1000 training runs."
  }
}
```

## Schema Versioning Policy

### Version 1 (Legacy)
- Single version field (`v: 1`)
- Minimal optimization for small payload size
- Stories split into `r` (Reddit) and `h` (HN) arrays
- No AI summary

### Version 2
- Added optional `summary` field with AI-generated content (simple/structured/fullBrief)
- Maintains backward compatibility with v1 readers

### Version 3
- Added optional `rs` (RSS stories) array

### Version 4 (Current)
- Added `metrics` block: runtime, scraping (with `extractor_breakdown`), ranking,
  summary, `analysis`, `quality` (coverage + scrape success + source counts),
  cost, and degradation
- Stories carry `rank`, `content_available`, `content_quality`, `excerpt`, and
  (HN) `discussion_context`
- `summary.analysis` added (optional; present when `AI_DIGEST_ANALYSIS_ENABLED=1`)

### Version Upgrades

| Version | Change |
|---------|--------|
| 1 → 2 | Added optional `summary` field with AI-generated DigestSummary |
| 2 → 3 | Added optional `rs` (RSS) stories array |
| 3 → 4 | Added `metrics` block, story ranking/quality metadata, and `summary.analysis` |

**Version check in TypeScript:**

```typescript
// In fetchDigest() - version check
if (data.v !== 2 && data.v !== 3 && data.v !== 4) {
  throw new Error(`Unsupported digest version: ${data.v}`);
}

// Accessing optional fields (with fallback)
const summary = data.summary;
if (summary) {
  console.log(summary.simple);
  if (summary.analysis) {
    console.log(summary.analysis.skeptic_take);
  }
}
```

### Client Compatibility

```typescript
// Version-agnostic digest handling
function handleDigest(data: Digest) {
  // Always available
  console.log(data.v, data.d, data.r, data.h);

  // V3+ (optional)
  const rss = data.rs ?? [];

  // V2+ (optional)
  if (data.summary) {
    displaySummary(data.summary);
    if (data.summary.analysis) {
      displayAnalysis(data.summary.analysis);
    }
  }
}
```

## File Location

The `digest.json` file is served from:
```
public/data/digest.json
```

Deployed to:
```
https://your-domain.vercel.app/data/digest.json
```

## Generated Output

The Python scripts generate two output files:
- `digest.json` - Structured data for the web reader
- `digest.md` - Human-readable markdown digest

```
output/
└── 2026-04-15/
    ├── digest-2026-04-15-090000.json
    └── digest-2026-04-15-090000.md
```
