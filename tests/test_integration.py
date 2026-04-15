def test_full_digest_format():
    """Test the full pipeline works."""
    from fetchers import fetch_reddit_posts, fetch_hn_posts
    from formatter import format_digest
    from datetime import date
    
    reddit = fetch_reddit_posts("ArtificialIntelligence", limit=3)
    hn = fetch_hn_posts(limit=3)
    
    digest = format_digest(reddit, hn, date.today().strftime("%Y-%m-%d"))
    
    assert "AI Digest" in digest
    assert len(digest) > 0
