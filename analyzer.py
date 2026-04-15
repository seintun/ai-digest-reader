"""Claude CLI integration for AI-powered digest summary generation."""
import subprocess
import json
from typing import Dict, Any, List, Optional


def generate_summary(reddit_posts: List[Dict], hn_posts: List[Dict]) -> Optional[Dict[str, Any]]:
    """
    Calls claude CLI with all stories, returns validated structured JSON.
    Retries once if validation fails. Returns None if analysis fails.
    """
    from schema import validate_summary

    prompt = _build_prompt(reddit_posts, hn_posts)

    try:
        result = subprocess.run(
            ["claude", "--print", prompt],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            print(f"Claude CLI error: {result.stderr}")
            return None

        parsed = _parse_claude_response(result.stdout)
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
        result2 = subprocess.run(
            ["claude", "--print", retry_prompt],
            capture_output=True,
            text=True,
            timeout=60
        )
        parsed2 = _parse_claude_response(result2.stdout)
        if parsed2 and validate_summary(parsed2):
            return parsed2

        print("Warning: Summary failed schema validation after retry. Summary will be omitted.")
        return None

    except FileNotFoundError:
        print("Warning: claude CLI not found. Install with: npm install -g @anthropic-ai/claude-code")
        return None
    except subprocess.TimeoutExpired:
        print("Warning: Claude CLI timed out after 60s")
        return None
    except Exception as e:
        print(f"Warning: Claude analysis failed: {e}")
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
        print(f"Warning: Failed to parse Claude JSON: {e}")
        return None
