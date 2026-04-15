# Data Schema

## Digest Structure

```typescript
interface Digest {
  v: 1 | 2;              // Schema version
  d: string;             // Digest date (YYYY-MM-DD)
  g: string;             // Generated timestamp (ISO 8601)
  r: Story[];            // Reddit stories
  h: Story[];            // Hacker News stories
  summary?: DigestSummary; // AI-generated summary (v2+)
}
```

## Story Structure

```typescript
interface Story {
  i: string;      // ID (format: "rd-{n}" or "hn-{n}")
  t: string;      // Title
  u: string;      // URL
  s: number;      // Score (upvotes/comments)
  c: number;      // Comment count
  a: string;      // Author
}
```

## DigestSummary Structure (v2+)

`schema.py` is the Python single source of truth for this shape. The TypeScript mirror lives in `src/types.ts`.

```typescript
interface DigestSummary {
  schema_version: string;  // Always "2" for current output
  simple: string;          // 2-3 sentence TL;DR
  structured: Structured;  // Themes, breaking headline, must-reads
  fullBrief: FullBrief;   // Structured long-form briefing
}

interface Structured {
  themes: string[];        // Key themes/trends (3 items typical)
  breaking: string;        // Single breaking headline sentence
  mustRead: MustReadItem[]; // Essential reading
}

interface FullBrief {
  intro: string;                // Opening paragraph
  sections: FullBriefSection[]; // Body sections
  closing: string;              // One-sentence takeaway
}

interface FullBriefSection {
  heading: string;  // Section title
  body: string;     // Paragraph text
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
| `simple` | string | One-line overview of the day's news | `"AI advances dominated..."` |
| `themes` | string[] | Key themes and trends | `["Multimodal AI", "Open Source"]` |
| `breaking` | string[] | Breaking news items | `["Anthropic releases Claude 4"]` |
| `mustRead` | MustReadItem[] | Essential reading with reasoning | `[{title, url, source, reason}]` |
| `fullBrief` | string | 2-3 paragraph detailed briefing | `"Major developments..."` |

### MustReadItem Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `title` | string | Article title | `"Claude 4 Technical Report"` |
| `url` | string | Direct URL to article | `"https://anthropic.com/..."` |
| `source` | string | Source platform | `"reddit"` or `"hn"` |
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

### Version 2 (Current)
- Version field updated to `v: 2`
- Added optional `summary` field with AI-generated content
- Maintains backward compatibility with v1 readers
- DigestSummary includes: simple, themes, breaking, mustRead, fullBrief

### Version Upgrades

| Version | Change |
|---------|--------|
| 1 → 2 | Added optional `summary` field with AI-generated DigestSummary |
| 2+ | Reserved for future breaking changes |

**Upgrading from v1 to v2:**
1. Update version number in Python generator
2. Add `analyzer.py` for AI summary generation
3. Summary field is optional - v1 readers can ignore it
4. Update this documentation

**Version check in TypeScript:**

```typescript
// In fetchDigest() - version check
if (data.v !== 1 && data.v !== 2) {
  throw new Error(`Unsupported digest version: ${data.v}`);
}

// Accessing v2 summary (with fallback)
const summary = data.summary;
if (summary) {
  console.log(summary.simple);
}
```

### Client Compatibility

```typescript
// Version-agnostic digest handling
function handleDigest(data: Digest) {
  // Always available
  console.log(data.v, data.d, data.r, data.h);
  
  // V2+ only (optional)
  if (data.v >= 2 && data.summary) {
    displaySummary(data.summary);
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
