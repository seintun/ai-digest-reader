# AI Summarization Architecture

## Overview
`analyzer.py` generates structured AI summaries of the day's digest using a two-tier approach: OpenRouter API (preferred) with Claude CLI as fallback.

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

## Retry Logic
On schema validation failure, the prompt is re-sent with an appended "CRITICAL: follow schema exactly" instruction. One retry only.

## Adding a New Model
Set `OPENROUTER_API_KEY` and change the model in `_call_openrouter()`:
```python
model="moonshotai/kimi-k2"  # or "x-ai/grok-4-0131", "google/gemini-flash-1.5", etc.
```
See https://openrouter.ai/models for available models and pricing.
