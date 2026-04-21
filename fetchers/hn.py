import re
from concurrent.futures import ThreadPoolExecutor

import requests
from config import HN_API_URL, POST_LIMIT


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


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
