"""AI summary generator using OpenRouter API with Claude CLI fallback."""
import json
import os
import subprocess
from typing import Dict, Any, List, Optional, Tuple

from model_pricing import usage_to_dict
from schema import validate_summary

OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "moonshotai/kimi-k2.6")
SUMMARY_AI_CONNECT_TIMEOUT = float(os.environ.get("SUMMARY_AI_CONNECT_TIMEOUT", "10") or "10")
SUMMARY_AI_READ_TIMEOUT = float(os.environ.get("SUMMARY_AI_READ_TIMEOUT", "20") or "20")
CLAUDE_CLI_TIMEOUT_SECONDS = int(os.environ.get("CLAUDE_CLI_TIMEOUT_SECONDS", "20") or "20")


def generate_summary(reddit_posts: List[Dict], hn_posts: List[Dict]) -> Optional[Dict[str, Any]]:
    """
    Calls OpenRouter API (with Claude CLI fallback), returns validated structured JSON.
    Retries once if validation fails. Returns None if analysis fails.
    """
    prompt = _build_prompt(reddit_posts, hn_posts)

    raw = _call_openrouter(prompt)
    if raw is None:
        raw = _call_claude_cli(prompt)
    if raw is None:
        return None

    parsed = _parse_claude_response(raw)
    if parsed and validate_summary(parsed):
        return parsed

    # Retry once with a stricter instruction
    print("Warning: Summary failed schema validation — retrying with stricter prompt.")
    retry_prompt = (
        prompt
        + "\n\nCRITICAL: Your previous response did not match the required schema. "
        "Output ONLY the raw JSON object. No text before or after. "
        "schema_version must be \"2\". mustRead must have exactly 3 items. "
        "fullBrief must have intro, sections (2-4 items), and closing. "
        "All values must be plain text strings — no markdown."
    )

    raw2 = _call_openrouter(retry_prompt)
    if raw2 is None:
        raw2 = _call_claude_cli(retry_prompt)
    if raw2 is None:
        print("Warning: Summary failed schema validation after retry. Summary will be omitted.")
        return None

    parsed2 = _parse_claude_response(raw2)
    if parsed2 and validate_summary(parsed2):
        return parsed2

    print("Warning: Summary failed schema validation after retry. Summary will be omitted.")
    return None


def _call_openrouter(prompt: str) -> Optional[str]:
    """Call OpenRouter API. Returns raw response text or None."""
    raw, _ = _call_openrouter_with_usage(prompt)
    return raw


def _call_openrouter_with_usage(prompt: str) -> Tuple[Optional[str], Dict[str, float | int | str]]:
    """Call OpenRouter API. Returns (raw response text or None, token usage)."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return None, usage_to_dict(0, 0)
    try:
        body = json.dumps(
            {
                "model": OPENROUTER_MODEL,
                "messages": [{"role": "user", "content": prompt}],
            }
        )
        max_time = max(1, int(SUMMARY_AI_CONNECT_TIMEOUT + SUMMARY_AI_READ_TIMEOUT))
        result = subprocess.run(
            [
                "curl",
                "-sS",
                "--max-time",
                str(max_time),
                "-X",
                "POST",
                "https://openrouter.ai/api/v1/chat/completions",
                "-H",
                f"Authorization: Bearer {api_key}",
                "-H",
                "Content-Type: application/json",
                "-H",
                "HTTP-Referer: https://dailydigest.vercel.app",
                "-H",
                "X-Title: DailyDigest",
                "--data",
                body,
            ],
            capture_output=True,
            text=True,
            timeout=max_time + 3,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or f"curl_exit_{result.returncode}")
        payload = json.loads(result.stdout or "{}")
        if payload.get("error"):
            raise RuntimeError(str(payload.get("error")))
        usage = payload.get("usage", {}) or {}
        # Token accounting is intentionally direct and explicit.
        input_tokens = int(usage.get("prompt_tokens", 0) or 0)
        output_tokens = int(usage.get("completion_tokens", 0) or 0)
        usage_payload = usage_to_dict(
            input_tokens,
            output_tokens,
            openrouter_usage=usage,
            cost_source="openrouter_usage",
        )
        usage_payload["total_tokens"] = int(usage.get("total_tokens", input_tokens + output_tokens) or (input_tokens + output_tokens))
        choices = payload.get("choices", [])
        content = ""
        if choices:
            content = ((choices[0] or {}).get("message") or {}).get("content") or ""
        return content or None, usage_payload
    except Exception as e:
        print(f"OpenRouter API error: {e}")
        return None, usage_to_dict(0, 0)


def _call_claude_cli(prompt: str) -> Optional[str]:
    """Call Claude CLI subprocess. Returns raw response text or None."""
    try:
        result = subprocess.run(
            ["claude", "--print", prompt],
            capture_output=True,
            text=True,
            timeout=CLAUDE_CLI_TIMEOUT_SECONDS,
        )
        if result.returncode != 0:
            print(f"Claude CLI error: {result.stderr}")
            return None
        return result.stdout
    except FileNotFoundError:
        print("Warning: claude CLI not found. Install with: npm install -g @anthropic-ai/claude-code")
        return None
    except subprocess.TimeoutExpired:
        print(f"Warning: Claude CLI timed out after {CLAUDE_CLI_TIMEOUT_SECONDS}s")
        return None
    except Exception as e:
        print(f"Warning: Claude CLI failed: {e}")
        return None


def _build_prompt(reddit_posts: List[Dict], hn_posts: List[Dict]) -> str:
    """Build prompt with few-shot example enforcing strict schema."""
    lines = ["Analyze these AI/tech news stories and return a JSON summary.\n"]

    lines.append("## Reddit Stories")
    for i, post in enumerate(reddit_posts):
        story_id = f"rd-{i}"
        title = post.get('title', post.get('t', ''))
        url = post.get('url', post.get('u', ''))
        score = post.get('score', post.get('s', 0))
        comments = post.get('comments', post.get('c', 0))
        subreddit = post.get('subreddit', '')
        lines.append(f"- [{story_id}] [{subreddit}] {title} (score: {score}, comments: {comments})\n  URL: {url}")

    lines.append("\n## Hacker News Stories")
    for i, post in enumerate(hn_posts):
        story_id = f"hn-{i}"
        title = post.get('title', post.get('t', ''))
        url = post.get('url', post.get('u', ''))
        score = post.get('score', post.get('s', 0))
        comments = post.get('comments', post.get('c', 0))
        lines.append(f"- [{story_id}] {title} (score: {score}, comments: {comments})\n  URL: {url}")

    lines.append("""
OUTPUT RULES — read carefully:
1. Output ONLY a single raw JSON object. No markdown. No code blocks. No explanation.
2. All string values are plain text — no markdown syntax (no **, no ##, no *, no `).
3. schema_version must be exactly "2".
4. structured.themes must have exactly 3 strings.
5. structured.mustRead must have exactly 3 items.
6. fullBrief.sections must have 2-4 items.
7. Use story IDs from the list above (e.g. "rd-0", "hn-2") in mustRead[].id.

EXACT OUTPUT FORMAT — copy this structure:
{
  "schema_version": "2",
  "simple": "Two to three sentence plain text summary covering the main themes of today's digest.",
  "structured": {
    "themes": ["Theme One", "Theme Two", "Theme Three"],
    "breaking": "One sentence describing the single most significant story today.",
    "mustRead": [
      {
        "id": "rd-0",
        "title": "Exact story title here",
        "url": "https://example.com/story",
        "reason": "One sentence explaining why this story matters."
      },
      {
        "id": "hn-1",
        "title": "Exact story title here",
        "url": "https://example.com/story",
        "reason": "One sentence explaining why this story matters."
      },
      {
        "id": "rd-2",
        "title": "Exact story title here",
        "url": "https://example.com/story",
        "reason": "One sentence explaining why this story matters."
      }
    ]
  },
  "fullBrief": {
    "intro": "One paragraph plain text overview of the day's most important themes.",
    "sections": [
      {
        "heading": "Section One Title",
        "body": "One paragraph of plain text analysis for this section."
      },
      {
        "heading": "Section Two Title",
        "body": "One paragraph of plain text analysis for this section."
      },
      {
        "heading": "Section Three Title",
        "body": "One paragraph of plain text analysis for this section."
      }
    ],
    "closing": "One sentence takeaway or forward-looking observation."
  }
}
""")

    return "\n".join(lines)


def _parse_claude_response(response: str) -> Optional[Dict[str, Any]]:
    """Parse JSON from Claude output, handling accidental markdown code fences."""
    text = response.strip()

    if text.startswith("```"):
        parts = text.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{"):
                text = part
                break

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        decoder = json.JSONDecoder()
        start = text.find("{")
        while start != -1:
            try:
                parsed, _ = decoder.raw_decode(text[start:])
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass
            start = text.find("{", start + 1)

        print(f"Warning: Failed to parse Claude JSON: {e}")
        return None
