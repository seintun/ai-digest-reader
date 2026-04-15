from fetchers.reddit import fetch_reddit_posts

def test_fetch_returns_list():
    posts = fetch_reddit_posts("ArtificialIntelligence", limit=5)
    assert isinstance(posts, list)
