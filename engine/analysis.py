"""Stage-3 analysis: devil's-advocate implications layered on the base summary.

This is an *additive* enhancement over the schema-v2 summary. The base summary
(simple / structured / fullBrief) is produced exactly as before; this module
runs one extra LLM call to produce an ``analysis`` block:

    {
      "implications": ["for engineers", "for the industry"],
      "skeptic_take": "strongest counter-argument",
      "confidence": "high|medium|low",
      "evidence_basis": ["what is verified vs title-only"]
    }

It reuses the Hermes CLI plumbing from engine.summary so there is a single
battle-tested path for shelling out to ``hermes chat``. Gated by
``AI_DIGEST_ANALYSIS_ENABLED`` (default off) so the working v2 path is untouched
until explicitly opted in.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from schema import parse_llm_json
from .config import DigestEngineConfig
from .summary import _hermes_command

_VALID_CONFIDENCE = {"high", "medium", "low"}

_ANALYSIS_SYSTEM_PROMPT = """\
You are a skeptical senior technology analyst. Given a daily AI news digest
summary and its ranked stories, produce a decision-useful analysis.

Output ONLY a single raw JSON object matching this schema exactly:
{
  "implications": ["<what this means for practicing engineers>", "<what this means for the industry>"],
  "skeptic_take": "<the strongest counter-argument or reason for caution, one or two sentences>",
  "confidence": "high" | "medium" | "low",
  "evidence_basis": ["<which claims are corroborated by primary sources>", "<which are title-only or single-source>"]
}
Rules: No markdown. All values plain strings except implications/evidence_basis
which are string arrays. confidence MUST be one of high/medium/low. implications
must have 1-3 items. evidence_basis must have 1-4 items. Be concrete and honest;
flag hype, single-source rumors, and unverified metrics explicitly."""


def validate_analysis(data: Any) -> bool:
    """Validate the analysis block shape. Returns False on any violation."""
    if not isinstance(data, dict):
        return False

    implications = data.get("implications")
    if not isinstance(implications, list) or not (1 <= len(implications) <= 3):
        return False
    if not all(isinstance(x, str) and x.strip() for x in implications):
        return False

    skeptic = data.get("skeptic_take")
    if not isinstance(skeptic, str) or not skeptic.strip():
        return False

    confidence = data.get("confidence")
    if confidence not in _VALID_CONFIDENCE:
        return False

    evidence = data.get("evidence_basis")
    if not isinstance(evidence, list) or not (1 <= len(evidence) <= 4):
        return False
    if not all(isinstance(x, str) and x.strip() for x in evidence):
        return False

    return True


def _evidence_label(post: Dict[str, Any]) -> str:
    return "verified-content" if post.get("content_available") else "title-only"


def _build_analysis_prompt(summary: Dict[str, Any], ranked_posts: List[Dict[str, Any]]) -> str:
    structured = summary.get("structured", {}) if isinstance(summary, dict) else {}
    themes = structured.get("themes", []) if isinstance(structured, dict) else []
    breaking = structured.get("breaking", "") if isinstance(structured, dict) else ""

    lines = [
        "Analyze this AI news digest and return the analysis JSON.",
        "",
        "## Digest TL;DR",
        str(summary.get("simple", "") if isinstance(summary, dict) else ""),
        "",
        "## Breaking",
        str(breaking),
        "",
        "## Themes",
        ", ".join(str(t) for t in themes) if themes else "(none)",
        "",
        "## Ranked stories (with evidence status)",
    ]
    for post in ranked_posts:
        story_id = post.get("i", "")
        title = post.get("t", "")
        lines.append(f"[{story_id}] {title} | evidence:{_evidence_label(post)}")
    return "\n".join(lines)


def _hermes_analysis_command(config: DigestEngineConfig, prompt: str) -> Tuple[Optional[str], Dict[str, Any]]:
    """Thin wrapper so tests can patch the LLM call without touching summary.py."""
    full_prompt = _ANALYSIS_SYSTEM_PROMPT + "\n\n" + prompt
    return _hermes_command(config, full_prompt)


def generate_analysis_with_hermes(
    summary: Dict[str, Any],
    ranked_posts: List[Dict[str, Any]],
    config: DigestEngineConfig,
) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    """Run the stage-3 analysis call. Returns (analysis_dict_or_None, meta)."""
    if not summary or not ranked_posts:
        return None, {"source": "analysis", "generated": False, "error": "missing summary or posts"}

    prompt = _build_analysis_prompt(summary, ranked_posts)
    content, usage = _hermes_analysis_command(config, prompt)
    if not content:
        return None, {
            "source": "analysis",
            "generated": False,
            "error": usage.get("stderr") or usage.get("cost_source") or "no analysis content",
            "usage": usage,
        }

    # parse_llm_json tolerates CLI preamble (warnings, reasoning boxes) and code
    # fences by scanning for the first decodable JSON object.
    parsed = parse_llm_json(content)
    if parsed is None:
        return None, {"source": "analysis", "generated": False, "error": "analysis not valid JSON", "usage": usage}

    if not validate_analysis(parsed):
        return None, {"source": "analysis", "generated": False, "error": "analysis failed schema validation", "usage": usage}

    return parsed, {
        "source": "analysis",
        "generated": True,
        "usage": usage,
        "confidence": parsed.get("confidence"),
    }
