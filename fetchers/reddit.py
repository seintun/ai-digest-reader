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
    """Fetch top posts from a subreddit. Uses multiple fallback methods."""
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

            post_list = _extract_post_list(data, limit)
            for post in post_list:
                posts.append(_normalize_reddit_post(post, subreddit))
                if len(posts) >= limit:
                    break
            
            if posts:
                break
        except (requests.RequestException, ValueError):
            continue
    
    return posts[:limit]
