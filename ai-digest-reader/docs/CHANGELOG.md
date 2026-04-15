# Changelog

All notable changes to the AI News Digest Aggregator project.

## [Unreleased] - Strict v2 Summary Schema

### Added
- **`schema.py`** — Python `TypedDict` single source of truth for `DigestSummary` contract (`MustReadItem`, `FullBriefSection`, `FullBrief`, `Structured`, `DigestSummary`)
- **`validate_summary()`** in `schema.py` — validates all required fields, types, and cardinality (themes=3, mustRead=3, sections≥2)
- **Retry logic** in `analyzer.py` — retries once with stricter prompt on schema validation failure
- **Few-shot prompt** in `analyzer.py` — exact JSON example enforces v2 output shape from Claude
- **Zod schema** in `digest.ts` — `DigestSummarySchema` mirrors the Python contract
- **`validateSummary()`** in `digest.ts` — uses `safeParse` (never throws), degrades gracefully
- **`FullBriefSection`** and **`FullBrief`** TypeScript interfaces in `types.ts`
- **72 tests** across `test_schema.py` (40) and `test_analyzer.py` (32)

### Changed
- `MustReadItem.t` → `MustReadItem.title` (readable, explicit field name)
- `DigestSummary.fullBrief` type: `string` → `FullBrief` structured object
- `DigestSummary` now includes `schema_version: string` (always `"2"`)
- Full Brief card renders structured `intro / sections[] / closing` instead of parsed markdown
- All summary card strings now wrapped in `escapeHtml()` for XSS safety
- Version check in `fetchDigest()` accepts both `v: 1` and `v: 2`

### Removed
- `renderMarkdown()` and `formatInlineMarkdown()` functions (replaced by structured rendering)
- Local `DigestResponse` interface in `digest.ts` (replaced by `Digest` from `types.ts`)

---

## [2.0.0] - 2026-04-15

### Added

#### AI Summary Feature
- **Claude-powered summaries** - AI-generated daily briefings via Claude CLI
- **DigestSummary component** - Tabbed display for themes, breaking news, and must-read articles
- **Schema v2** - Extended data schema with optional `summary` field
- **MustReadItem structure** - Curated articles with reasons for reading
- **analyzer.py** - New script for AI summary generation

#### Documentation
- **DATA_SCHEMA.md** - Complete v2 schema documentation
- **ARCHITECTURE.md** - Updated architecture with AI flow
- **TROUBLESHOOTING.md** - Common issues and solutions
- **diagrams/** - ASCII architecture diagrams

### Changed

#### Data Schema
- Schema version: `v: 1` → `v: 1 | 2`
- Added optional `summary` field with DigestSummary structure
- Maintains backward compatibility with v1 readers

#### Output
- Generates both `digest.json` (v2) and `digest.md`
- JSON output includes AI summary when available

### Features

| Feature | Description |
|---------|-------------|
| Simple Overview | One-line summary of the day's news |
| Theme Detection | Key themes and trends identified by AI |
| Breaking News | Urgent or important items highlighted |
| Must-Read | Curated essential articles with reasoning |
| Full Brief | 2-3 paragraph detailed briefing |

### Breaking Changes

| Change | Impact |
|--------|--------|
| `--no-ai` flag | New flag to skip AI summary generation |
| Schema v2 | Optional field - v1 readers continue to work |
| Claude CLI required | For AI summaries - use `--no-ai` as fallback |

### Backend

- **aggregator.py** - Enhanced story fetching
- **analyzer.py** - NEW: Claude CLI integration for AI summaries
- **generator.py** - Main entry point with `--no-ai` option
- **config.py** - Shared configuration

### Frontend

- **DigestSummary.astro** - NEW: AI summary display component
- Tabbed interface: Overview | Themes | Breaking | Must-Read
- Graceful fallback when summary unavailable
- Cached with digest data in localStorage

### Documentation Updates

| Document | Changes |
|----------|---------|
| README.md (root) | Added --no-ai flag, JSON output info, Claude CLI requirement |
| docs/README.md | AI Summary feature, tabbed display, prerequisites |
| DATA_SCHEMA.md | v2 schema, DigestSummary, MustReadItem, examples |
| ARCHITECTURE.md | analyzer.py, AI summary flow, component hierarchy |
| TROUBLESHOOTING.md | NEW: Common issues and solutions |
| CHANGELOG.md | This file |
| diagrams/ | NEW: ARCHITECTURE.txt, DATA_FLOW.txt, SUMMARY_FLOW.txt |

---

## [1.0.0] - 2026-04-10

### Added

- Initial release
- Reddit and Hacker News aggregation
- Three view modes: Cards, List, Glance
- Source filtering
- Dark/Light mode
- PWA support with offline caching
- Responsive mobile-first design
- Vercel deployment configuration

### Features

| Feature | Description |
|---------|-------------|
| Multi-source | Reddit + Hacker News in one digest |
| Cards View | Visual card layout |
| List View | Compact text list |
| Glance View | Ultra-compact summary |
| Dark Mode | Auto-detect + manual toggle |
| Offline | Service worker caching |

### Data Schema v1

```typescript
interface Digest {
  v: 1;
  d: string;      // Date
  g: string;      // Generated timestamp
  r: Story[];     // Reddit stories
  h: Story[];     // HN stories
}
```

### Tech Stack

- Astro 4 + Tailwind CSS 3
- Vanilla JavaScript
- Python CLI for data generation
- Vercel deployment

---

## Migration Guide

### Upgrading from v1 to v2

1. **Install Claude CLI** (optional but recommended):
   ```bash
   brew install anthropic/anthropic/claude
   ```

2. **Update Python scripts**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Regenerate digest**:
   ```bash
   python scripts/generator.py > ai-digest-reader/public/data/digest.json
   ```

4. **Frontend compatibility**:
   - v2 is backward compatible with v1 readers
   - Summary field is optional - works without AI summaries
   - Use `--no-ai` to skip AI generation

### Using v2 Without AI

To generate v2-compatible digest without AI summaries:

```bash
python scripts/generator.py --no-ai > digest.json
```

The JSON will have `v: 2` but no `summary` field.

---

## Future Plans

- [ ] Custom summary styles
- [ ] Historical summary comparison
- [ ] Category filtering for summaries
- [ ] Multiple AI provider support
- [ ] Scheduled automatic generation
- [ ] Email/push notifications
