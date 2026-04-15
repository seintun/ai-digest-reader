"""Markdown formatter for digest output."""


def format_digest(reddit_posts: list, hn_posts: list, digest_date: str) -> str:
    """Format posts into markdown digest."""
    lines = [
        f"# AI Digest - {digest_date}",
        "",
        "## Reddit",
        "",
    ]
    
    for i, post in enumerate(reddit_posts, 1):
        lines.append(f"{i}. **{post['title']}**")
        lines.append(f"   - [{post['subreddit']}]({post['url']}) | {post['score']} points")
        lines.append("")
    
    if not reddit_posts:
        lines.append("*No Reddit posts available*")
        lines.append("")
    
    lines.extend([
        "## Hacker News",
        "",
    ])
    
    for i, post in enumerate(hn_posts, 1):
        lines.append(f"{i}. **{post['title']}**")
        lines.append(f"   - [{post['url']}]({post['score']}) | {post['score']} points")
        lines.append("")
    
    if not hn_posts:
        lines.append("*No Hacker News posts available*")
        lines.append("")
    
    return "\n".join(lines)