# Data Schema

## Digest Structure

```typescript
interface Digest {
  v: 1;           // Schema version
  d: string;      // Digest date (YYYY-MM-DD)
  g: string;      // Generated timestamp (ISO 8601)
  r: Story[];     // Reddit stories
  h: Story[];     // Hacker News stories
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

## Field Specifications

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `v` | number | Schema version (always `1`) | `1` |
| `d` | string | Digest date in YYYY-MM-DD format | `"2026-04-15"` |
| `g` | string | ISO 8601 timestamp of generation | `"2026-04-15T08:30:00+00:00"` |
| `r` | Story[] | Array of Reddit stories | `[{...}, {...}]` |
| `h` | Story[] | Array of Hacker News stories | `[{...}, {...}]` |

### Story Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `i` | string | Unique identifier with source prefix | `"rd-0"`, `"hn-5"` |
| `t` | string | Post/article title | `"GPT-5 released today"` |
| `u` | string | Direct URL to content | `"https://openai.com/blog/..."` |
| `s` | number | Score (upvotes on Reddit, points on HN) | `1523` |
| `c` | number | Number of comments | `342` |
| `a` | string | Author/username | `"sama"` |

## Example Data

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

## Schema Versioning Policy

### Version 1 (Current)
- Single version field (`v: 1`)
- Minimal optimization for small payload size
- Stories split into `r` (Reddit) and `h` (HN) arrays

### Version Upgrades

| Version | Change |
|---------|--------|
| 2+ | Reserved for future breaking changes |

When upgrading:
1. Update version number in Python generator
2. Add migration logic in `src/lib/digest.ts`
3. Update this documentation
4. Maintain backward compatibility when possible

### Client Compatibility

```typescript
// In fetchDigest() - version check
if (data.v !== 1) {
  throw new Error(`Unsupported digest version: ${data.v}`);
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
