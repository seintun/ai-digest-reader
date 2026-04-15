import re

import requests
from config import HN_API_URL, POST_LIMIT


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


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
    except Exception:
        return []
    
    if not story_ids:
        return []
    
    posts = []
    
    for story_id in story_ids:
        try:
            item_url = f"{HN_API_URL}/item/{story_id}.json"
            item_response = requests.get(item_url, timeout=10)
            
            if item_response.status_code == 200:
                story = item_response.json()
                if story and (story.get("url") or story.get("text")):
                    permalink = f"https://news.ycombinator.com/item?id={story_id}"
                    posts.append({
                        "title": story.get("title", ""),
                        "url": story.get("url", permalink),
                        "permalink": permalink,
                        "body": strip_html(story.get("text", ""))[:280].strip(),
                        "score": story.get("score", 0),
                        "author": story.get("by", ""),
                        "comments": story.get("descendants", 0),
                    })
        except requests.RequestException:
            continue
    
    return posts[:limit]
