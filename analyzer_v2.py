"""Content-aware summary generator using ranked stories."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from llm_client import LLMClient
from model_pricing import usage_to_dict
from schema import extract_excerpt, parse_llm_json, validate_summary

SUMMARY_RETRY_ATTEMPTS = max(1, int(os.environ.get("SUMMARY_V2_RETRY_ATTEMPTS", "1") or "1"))

_SYSTEM_PROMPT = """\
You are a tech news analyst. Output ONLY a single raw JSON object matching this schema exactly:
{
  "schema_version": "2",
  "simple": "<2-3 sentence plain text TL;DR>",
  "structured": {
    "themes": ["<theme1>", "<theme2>", "<theme3>"],
    "breaking": "<most significant story, one sentence>",
    "mustRead": [
      {"id": "<story_id>", "title": "<title>", "url": "<url>", "reason": "<one sentence>"},
      {"id": "<story_id>", "title": "<title>", "url": "<url>", "reason": "<one sentence>"},
      {"id": "<story_id>", "title": "<title>", "url": "<url>", "reason": "<one sentence>"}
    ]
  },
  "fullBrief": {
    "intro": "<one paragraph overview>",
    "sections": [
      {"heading": "<title>", "body": "<one paragraph>"},
      {"heading": "<title>", "body": "<one paragraph>"}
    ],
    "closing": "<one sentence takeaway>"
  }
}
Rules: No markdown. All values plain text strings. schema_version must be "2". \
themes must have exactly 3 strings. mustRead must have exactly 3 items. \
fullBrief.sections must have 2-4 items. Use story IDs from the input (e.g. "rd-0", "hn-2")."""


def _age_hours(post: Dict) -> float:
    ts = post.get("ts")
    if not ts:
        return 24.0
    try:
        return max(0.0, (datetime.now(timezone.utc).timestamp() - float(ts)) / 3600.0)
    except (TypeError, ValueError):
        return 24.0


def _source_label(post: Dict) -> str:
    sn = post.get("sn", "")
    if sn:
        return sn
    story_id = post.get("i", "")
    prefix = story_id.split("-", 1)[0] if story_id else ""
    return {"rd": "Reddit", "hn": "HN", "rs": "RSS"}.get(prefix, prefix or "?")


def _build_prompt(ranked_posts: List[Dict]) -> str:
    lines = ["Analyze these AI/tech news stories and return a JSON summary.", ""]
    lines.append("## Top Stories (Ranked by Importance)")
    for post in ranked_posts:
        story_id = post.get("i", "")
        title = post.get("t", "")
        url = post.get("u", "")
        rank = post.get("rank", 0)
        score = post.get("s", 0)
        quality = post.get("content_quality", 0)
        age = round(_age_hours(post))
        source = _source_label(post)
        raw_content = post.get("content", "") or post.get("excerpt", "") or post.get("b", "") or ""
        excerpt = extract_excerpt(raw_content, max_chars=200)
        lines.append(
            f"[{story_id}] [{rank}/100] {title} | src:{source} | age:{age}h | score:{score} | quality:{quality}/10"
        )
        if url:
            lines.append(f"url: {url}")
        if excerpt:
            lines.append(f'excerpt: "{excerpt}"')
        lines.append("")
    return "\n".join(lines)


def generate_summary(ranked_posts: List[Dict]) -> Optional[Dict[str, Any]]:
    """Generate a schema-v2 summary from ranked content-aware posts."""
    summary, _ = generate_summary_with_meta(ranked_posts)
    return summary


def generate_summary_with_meta(ranked_posts: List[Dict]) -> tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    """Generate schema-v2 summary with metadata about source/fallback behavior."""
    if not ranked_posts:
        return None, {"source": "none", "generated": False, "usage": usage_to_dict(0, 0)}

    client = LLMClient()
    base_prompt = _build_prompt(ranked_posts)
    latest_usage: Dict[str, Any] = usage_to_dict(0, 0)

    for attempt in range(SUMMARY_RETRY_ATTEMPTS):
        print(f"  summary attempt {attempt + 1}/{SUMMARY_RETRY_ATTEMPTS}...", flush=True)
        prompt = base_prompt
        if attempt > 0:
            prompt += (
                "\n\nCRITICAL RETRY: Previous output was invalid. "
                "Return ONLY one raw JSON object that strictly follows the schema rules."
            )
        content, usage = client.complete(prompt, system=_SYSTEM_PROMPT)
        latest_usage = usage
        if content is None:
            continue
        parsed = parse_llm_json(content)
        if parsed and validate_summary(parsed):
            source = "openrouter" if usage.get("input_tokens", 0) else "claude_cli"
            return parsed, {"source": source, "generated": True, "usage": usage}

    return None, {"source": "none", "generated": False, "usage": latest_usage}
