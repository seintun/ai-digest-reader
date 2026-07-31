import html as _html
import re
from concurrent.futures import ThreadPoolExecutor

import requests
from config import HN_API_URL, POST_LIMIT

HN_ALGOLIA_ITEMS_URL = "https://hn.algolia.com/api/v1/items"
COMMENT_MAX_CHARS = 500


def strip_html(text: str) -> str:
    return _html.unescape(re.sub(r"<[^>]+>", "", text))


def fetch_hn_top_comments(story_id: int, limit: int = 5) -> list[dict]:
    """Fetch the top comments for an HN story via the Algolia items endpoint.

    The Algolia ``items`` endpoint returns the whole comment tree in a single
    request, so this is one network call regardless of comment count. Comments
    are walked breadth-first to a shallow depth so a top-level comment and its
    immediate reply both surface. HTML is stripped and text truncated.

    Returns a list of ``{"author", "text", "depth"}`` dicts, up to ``limit``.
    Returns ``[]`` on any network/parse failure so callers degrade gracefully.
    """
    try:
        response = requests.get(f"{HN_ALGOLIA_ITEMS_URL}/{story_id}", timeout=10)
        if response.status_code != 200:
            return []
        item = response.json()
    except (requests.RequestException, ValueError):
        return []

    comments: list[dict] = []

    def _walk(children: list, depth: int = 0) -> None:
        for child in children or []:
            if not isinstance(child, dict):
                continue
            text = strip_html(child.get("text", "") or "").strip()
            if child.get("type") == "comment" and text:
                comments.append({
                    "author": child.get("author", ""),
                    "text": text[:COMMENT_MAX_CHARS],
                    "depth": depth,
                })
            if depth < 1:
                _walk(child.get("children") or [], depth + 1)

    _walk(item.get("children") or [])
    return comments[:limit]


def _fetch_item(story_id: int) -> dict | None:
    try:
        item_url = f"{HN_API_URL}/item/{story_id}.json"
        item_response = requests.get(item_url, timeout=10)
        if item_response.status_code != 200:
            return None

        story = item_response.json()
        if not story or not (story.get("url") or story.get("text")):
            return None

        permalink = f"https://news.ycombinator.com/item?id={story_id}"
        return {
            "title": story.get("title", ""),
            "url": story.get("url", permalink),
            "permalink": permalink,
            "body": strip_html(story.get("text", ""))[:280].strip(),
            "score": story.get("score", 0),
            "author": story.get("by", ""),
            "comments": story.get("descendants", 0),
            "ts": story.get("time"),
        }
    except requests.RequestException:
        return None
    except ValueError:
        return None


def fetch_hn_posts(limit: int = POST_LIMIT) -> list[dict]:
    """Fetch top stories from Hacker News."""
    top_stories_url = f"{HN_API_URL}/topstories.json"

    try:
        response = requests.get(top_stories_url, timeout=10)
        response.raise_for_status()
    except requests.RequestException:
        return []

    try:
        story_ids = response.json()[:limit]
    except ValueError:
        return []

    if not story_ids:
        return []

    workers = min(len(story_ids), 8)
    posts: list[dict] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for post in pool.map(_fetch_item, story_ids):
            if post:
                posts.append(post)

    return posts[:limit]
