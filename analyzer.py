"""AI summary generator using OpenRouter API with Claude CLI fallback."""
import json
import os
import subprocess
from typing import Dict, Any, List, Optional, Tuple

from schema import validate_summary


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


def _call_openrouter_with_usage(prompt: str) -> Tuple[Optional[str], Dict[str, int]]:
    """Call OpenRouter API. Returns (raw response text or None, token usage)."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return None, {"input_tokens": 0, "output_tokens": 0}
    try:
        from openai import OpenAI
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            default_headers={
                "HTTP-Referer": "https://dailydigest.vercel.app",
                "X-Title": "DailyDigest",
            },
        )
        response = client.chat.completions.create(
            model="moonshotai/kimi-k2.6",
            messages=[{"role": "user", "content": prompt}],
            timeout=90,
        )
        usage = response.usage
        input_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        output_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        return response.choices[0].message.content, {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }
    except ImportError:
        print("openai package not installed, falling back to Claude CLI")
        return None, {"input_tokens": 0, "output_tokens": 0}
    except Exception as e:
        print(f"OpenRouter API error: {e}")
        return None, {"input_tokens": 0, "output_tokens": 0}


def _call_claude_cli(prompt: str) -> Optional[str]:
    """Call Claude CLI subprocess. Returns raw response text or None."""
    try:
        result = subprocess.run(
            ["claude", "--print", prompt],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            print(f"Claude CLI error: {result.stderr}")
            return None
        return result.stdout
    except FileNotFoundError:
        print("Warning: claude CLI not found. Install with: npm install -g @anthropic-ai/claude-code")
        return None
    except subprocess.TimeoutExpired:
        print("Warning: Claude CLI timed out after 60s")
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
