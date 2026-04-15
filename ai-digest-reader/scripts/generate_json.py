#!/usr/bin/env python3
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import requests
from config import SUBREDDITS, HN_API_URL, POST_LIMIT


def fetch_reddit_posts(subreddit: str, limit: int = POST_LIMIT) -> list[dict]:
    posts = []
    for url_template in [
        "https://api.pushshift.io/reddit/search/submission/?subreddit={}&size={}&sort=desc&sort_type=score",
        "https://api.reddit.com/r/{}/hot?limit={}",
    ]:
        url = url_template.format(subreddit, limit)
        headers = {"User-Agent": "AIDigest/1.0"}
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                continue
            data = response.json()
            if "data" in data:
                data_section = data["data"]
                if isinstance(data_section, list):
                    post_list = data_section[:limit]
                elif "children" in data_section:
                    post_list = [c["data"] for c in data_section.get("children", [])[:limit]]
                else:
                    post_list = []
                for post in post_list:
                    posts.append({
                        "title": post.get("title", ""),
                        "url": post.get("url", post.get("permalink", "")),
                        "score": post.get("score", 0),
                        "subreddit": post.get("subreddit", subreddit),
                        "author": post.get("author", ""),
                        "comments": post.get("num_comments", 0),
                    })
                    if len(posts) >= limit:
                        break
            elif "children" in data:
                for child in data.get("children", [])[:limit]:
                    post = child.get("data", {})
                    posts.append({
                        "title": post.get("title", ""),
                        "url": f"https://reddit.com{post.get('permalink', '')}",
                        "score": post.get("score", 0),
                        "subreddit": post.get("subreddit", subreddit),
                        "author": post.get("author", ""),
                        "comments": post.get("num_comments", 0),
                    })
            if posts:
                break
        except requests.RequestException:
            continue
    return posts[:limit]


def fetch_hn_posts(limit: int = POST_LIMIT) -> list[dict]:
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
                if story and story.get("url"):
                    posts.append({
                        "title": story.get("title", ""),
                        "url": story.get("url", ""),
                        "score": story.get("score", 0),
                        "author": story.get("by", ""),
                        "comments": story.get("descendants", 0),
                    })
        except requests.RequestException:
            continue
    return posts[:limit]


def fetch_all_reddit_posts() -> list[dict]:
    all_posts = []
    for subreddit in SUBREDDITS:
        posts = fetch_reddit_posts(subreddit)
        all_posts.extend(posts)
    return all_posts


def generate_json(output_file: str | None = None) -> dict:
    now = datetime.now(timezone.utc)
    reddit_posts = fetch_all_reddit_posts()
    hn_posts = fetch_hn_posts()

    reddit_stories = [
        {
            "i": f"rd-{idx}",
            "t": post["title"],
            "u": post["url"],
            "s": post["score"],
            "c": post["comments"],
            "a": post["author"],
        }
        for idx, post in enumerate(reddit_posts)
    ]

    hn_stories = [
        {
            "i": f"hn-{idx}",
            "t": post["title"],
            "u": post["url"],
            "s": post["score"],
            "c": post["comments"],
            "a": post["author"],
        }
        for idx, post in enumerate(hn_posts)
    ]

    result = {
        "v": 1,
        "d": now.strftime("%Y-%m-%d"),
        "g": now.isoformat(),
        "r": reddit_stories,
        "h": hn_stories,
    }

    if output_file:
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2)
    else:
        print(json.dumps(result, indent=2))

    return result


if __name__ == "__main__":
    output = sys.argv[1] if len(sys.argv) > 1 else None
    generate_json(output)
