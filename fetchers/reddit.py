import feedparser
import requests
from config import POST_LIMIT


def _normalize_reddit_post(post: dict, subreddit: str) -> dict:
    permalink = f"https://reddit.com{post.get('permalink', '')}"
    return {
        "title": post.get("title", ""),
        "url": post.get("url", permalink),
        "permalink": permalink,
        "body": post.get("selftext", "")[:280].replace("\n", " ").strip(),
        "score": post.get("score", 0),
        "subreddit": post.get("subreddit", subreddit),
        "author": post.get("author", ""),
        "comments": post.get("num_comments", 0),
        "ts": post.get("created_utc"),
    }


def _extract_post_list(data: dict, limit: int) -> list[dict]:
    if "data" in data:
        data_section = data["data"]
        if isinstance(data_section, list):
            return data_section[:limit]
        if isinstance(data_section, dict) and "children" in data_section:
            children = data_section.get("children", [])
            return [c.get("data", {}) for c in children[:limit]]
        return []

    if "children" in data:
        return [child.get("data", {}) for child in data.get("children", [])[:limit]]

    return []


def fetch_reddit_posts(subreddit: str, limit: int = POST_LIMIT) -> list[dict]:
    """Fetch top posts from a subreddit. Uses JSON API with RSS fallback."""
    posts = []
    headers = {"User-Agent": "AIDigest/1.0"}

    for url_template in [
        "https://www.reddit.com/r/{}/hot.json?limit={}",
        "https://www.reddit.com/r/{}/top.json?limit={}&t=day",
    ]:
        url = url_template.format(subreddit, limit)
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                print(f"Reddit JSON {response.status_code} for r/{subreddit}: {url}")
                continue
            data = response.json()
            post_list = _extract_post_list(data, limit)
            for post in post_list:
                posts.append(_normalize_reddit_post(post, subreddit))
                if len(posts) >= limit:
                    break
            if posts:
                break
        except (requests.RequestException, ValueError) as e:
            print(f"Reddit JSON error for r/{subreddit}: {e}")
            continue

    if posts:
        return posts[:limit]

    # RSS fallback — more permissive in CI environments (no auth required)
    try:
        rss_url = f"https://www.reddit.com/r/{subreddit}/hot.rss?limit={limit}"
        feed = feedparser.parse(rss_url, request_headers={"User-Agent": "AIDigest/1.0"})
        for entry in feed.entries[:limit]:
            permalink = getattr(entry, "link", "")
            posts.append({
                "title": entry.get("title", ""),
                "url": permalink,
                "permalink": permalink,
                "body": "",
                "score": 0,
                "subreddit": subreddit,
                "author": "",
                "comments": 0,
                "ts": None,
            })
        if not posts:
            print(f"Reddit RSS fallback also empty for r/{subreddit}")
    except Exception as e:
        print(f"Reddit RSS fallback error for r/{subreddit}: {e}")

    return posts[:limit]
