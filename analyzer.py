"""Claude CLI integration for AI-powered digest summary generation."""
import subprocess
import json
from typing import Dict, Any, List, Optional


def generate_summary(reddit_posts: List[Dict], hn_posts: List[Dict]) -> Optional[Dict[str, Any]]:
    """
    Calls claude CLI with all stories, returns structured JSON.
    Returns None if analysis fails.
    """
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
            
        return _parse_claude_response(result.stdout)
        
    except FileNotFoundError:
        print("Warning: claude CLI not found. Install with: npm install -g @anthropic-ai/claude")
        print("Then authenticate with: claude auth login")
        return None
    except subprocess.TimeoutExpired:
        print("Warning: Claude CLI timed out after 60s")
        return None
    except Exception as e:
        print(f"Warning: Claude analysis failed: {e}")
        return None


def _build_prompt(reddit_posts: List[Dict], hn_posts: List[Dict]) -> str:
    """Build prompt with formatted stories."""
    lines = ["Analyze these AI news stories and generate a structured summary in JSON format.\n"]
    
    lines.append("## Reddit Stories")
    for post in reddit_posts:
        lines.append(f"- [{post['i']}] {post['t']} (score: {post['s']}, comments: {post['c']})")
    
    lines.append("\n## Hacker News Stories")
    for post in hn_posts:
        lines.append(f"- [{post['i']}] {post['t']} (score: {post['s']}, comments: {post['c']})")
    
    lines.append("""
Generate JSON with exactly this structure:
{
  "simple": "2-3 sentence TL;DR covering the main themes",
  "structured": {
    "themes": ["Theme 1", "Theme 2", "Theme 3"],
    "breaking": "One line on the most significant news",
    "mustRead": [
      {"id": "story-id", "t": "Story title", "url": "story-url", "reason": "Why this is must read"}
    ]
  },
  "fullBrief": "## Full Brief\n\nMarkdown content with sections..."
}

Rules:
- mustRead must have exactly 3 items
- Include the story URL for linking
- Keep reasons to 1 sentence
- fullBrief should be 3-5 paragraphs in markdown
- Output ONLY valid JSON, no markdown code blocks or explanation
""")
    
    return "\n".join(lines)


def _parse_claude_response(response: str) -> Optional[Dict[str, Any]]:
    """Parse JSON from Claude output."""
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
