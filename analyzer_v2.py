"""Content-aware summary generator using ranked stories."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from analyzer import _call_claude_cli, _call_openrouter_with_usage, _parse_claude_response
from model_pricing import usage_to_dict
from schema import validate_summary


def _build_prompt(ranked_posts: List[Dict]) -> str:
    lines = ["Analyze these AI/tech news stories and return a JSON summary.", ""]
    lines.append("## Top Stories (Ranked by Importance)")
    for post in ranked_posts:
        story_id = post.get("i", "")
        title = post.get("t", "")
        rank = post.get("rank", 0)
        score = post.get("s", 0)
        comments = post.get("c", 0)
        quality = post.get("content_quality", 0)
        content = (post.get("content", "") or post.get("excerpt", "") or post.get("b", ""))[:2000]
        lines.append(f"[{story_id}] [{rank}/100] {title}")
        lines.append(f"Content: {content}")
        lines.append(f"Score: {score}, Comments: {comments}, Quality: {quality}/10")
        lines.append("")

    lines.append(
        """
OUTPUT RULES — read carefully:
1. Output ONLY a single raw JSON object. No markdown. No code blocks. No explanation.
2. All string values are plain text — no markdown syntax (no **, no ##, no *, no `).
3. schema_version must be exactly "2".
4. structured.themes must have exactly 3 strings.
5. structured.mustRead must have exactly 3 items.
6. fullBrief.sections must have 2-4 items.
7. Use story IDs from the list above (e.g. "rd-0", "hn-2") in mustRead[].id.
"""
    )

    return "\n".join(lines)


def generate_summary(ranked_posts: List[Dict]) -> Optional[Dict[str, Any]]:
    """Generate a schema-v2 summary from ranked content-aware posts."""
    summary, _ = generate_summary_with_meta(ranked_posts)
    return summary


def generate_summary_with_meta(ranked_posts: List[Dict]) -> tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    """Generate schema-v2 summary with metadata about source/fallback behavior."""
    if not ranked_posts:
        return None, {"source": "none", "generated": False, "usage": usage_to_dict(0, 0)}

    prompt = _build_prompt(ranked_posts)
    raw, usage = _call_openrouter_with_usage(prompt)
    source = "openrouter"
    if raw is None:
        raw = _call_claude_cli(prompt)
        source = "claude_cli"
        usage = {"input_tokens": 0, "output_tokens": 0}
    if raw is None:
        return None, {"source": "none", "generated": False, "usage": usage_to_dict(0, 0)}

    parsed = _parse_claude_response(raw)
    if parsed and validate_summary(parsed):
        return parsed, {"source": source, "generated": True, "usage": usage_to_dict(usage["input_tokens"], usage["output_tokens"])}
    return None, {"source": source, "generated": False, "usage": usage_to_dict(usage["input_tokens"], usage["output_tokens"])}
