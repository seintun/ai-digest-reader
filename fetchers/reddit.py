import requests
from config import SUBREDDITS, POST_LIMIT


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