import sys
sys.path.insert(0, '/Users/seintun/code/claude_playground/dailydiget')
from formatter import format_digest

def test_format_creates_markdown():
    reddit_posts = [
        {"title": "Test Post", "url": "https://reddit.com/r/ai/test", "score": 100, "subreddit": "ai", "author": "user1", "comments": 50}
    ]
    content = format_digest(reddit_posts, [], "2026-04-14")
    assert "# AI Digest" in content
    assert "Test Post" in content