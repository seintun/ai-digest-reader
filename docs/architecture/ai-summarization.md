# AI Summarization Architecture

## Overview
DailyDigest v4 uses content-aware summarization:

1. `digest.py` ranks stories using `ranker.py`.
2. Top 15 ranked stories (with scraped content) are sent to `analyzer_v2.py`.
3. If v2 summarization fails, pipeline falls back to legacy `analyzer.py`.
4. If all summary paths fail, digest still ships without `summary`.

Both analyzers use a two-tier provider approach: OpenRouter API (preferred) with Claude CLI fallback.

## Provider Hierarchy
1. **OpenRouter API** (`OPENROUTER_API_KEY` env var) — primary
   - Model: `moonshotai/kimi-k2` (cost-effective, ~$0.15/M tokens)
   - Uses OpenAI-compatible SDK (`openai` package)
   - 90s timeout
2. **Claude CLI** (fallback, no API key needed) — user's Claude subscription
   - 60s timeout

## Schema (v2, unchanged)
The AI output schema has not changed from v2. The `generate_summary()` return type is `DigestSummary` TypedDict:
- `simple`: 2-3 sentence TL;DR
- `structured`: 3 themes + breaking news + 3 must-read items with links
- `fullBrief`: intro + 2-4 sections + closing

## Prompt Inputs
- `ranker.py` quality scoring prompt: up to 40 stories, each with max 200 chars.
- `analyzer_v2.py` summary prompt: top 15 stories, each with max 2000 chars.
- Both caps keep cost/runtime predictable and help hold the <$0.25 run target.

## Fallback and Degradation
1. **Primary summary**: `analyzer_v2.generate_summary_with_meta()`.
2. **Analyzer fallback**: `analyzer.generate_summary()` when v2 fails.
3. **No-summary mode**: when no provider returns valid schema output.

Per-run fallback status is recorded in `digest.json.metrics.degradation`.

## Validation Behavior
- `analyzer_v2.py` validates parsed responses with `schema.validate_summary()`.
- `analyzer.py` retains retry-on-validation-failure behavior with a stricter prompt for a second attempt.

## Adding a New Model
Set `OPENROUTER_API_KEY` and change the model in `analyzer.py` and `ranker.py` OpenRouter calls:
```python
model="moonshotai/kimi-k2"  # or "x-ai/grok-4-0131", "google/gemini-flash-1.5", etc.
```
See https://openrouter.ai/models for available models and pricing.
