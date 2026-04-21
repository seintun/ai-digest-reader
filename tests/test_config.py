from config import SUBREDDITS, SUBREDDIT_CATEGORIES, HN_API_URL, POST_LIMIT


def test_reddit_sources_is_unified():
    from config import REDDIT_SOURCES
    assert isinstance(REDDIT_SOURCES, list)
    assert len(REDDIT_SOURCES) == 24
    for src in REDDIT_SOURCES:
        assert 'name' in src and 'category' in src, f"Bad entry: {src}"


def test_subreddits_derived_from_sources():
    from config import REDDIT_SOURCES
    assert SUBREDDITS == [s["name"] for s in REDDIT_SOURCES]


def test_subreddit_categories_derived_from_sources():
    from config import REDDIT_SOURCES
    assert SUBREDDIT_CATEGORIES == {s["name"]: s["category"] for s in REDDIT_SOURCES}


def test_subreddit_categories_covers_all_subreddits():
    for sub in SUBREDDITS:
        assert sub in SUBREDDIT_CATEGORIES, f"Missing category for r/{sub}"


def test_new_categories_present():
    categories = set(SUBREDDIT_CATEGORIES.values())
    assert "Security" in categories
    assert "Business" in categories
    assert "AI & ML" in categories


def test_hn_configured():
    assert isinstance(HN_API_URL, str)
    assert POST_LIMIT == 10


def test_hn_category_is_string():
    from config import HN_CATEGORY
    assert isinstance(HN_CATEGORY, str)
    assert HN_CATEGORY


def test_rss_feeds_count():
    from config import RSS_FEEDS
    assert len(RSS_FEEDS) == 14


def test_rss_feeds_have_required_keys():
    from config import RSS_FEEDS
    for feed in RSS_FEEDS:
        assert 'url' in feed, f"Feed missing 'url': {feed}"
        assert 'name' in feed, f"Feed missing 'name': {feed}"
        assert 'category' in feed, f"Feed missing 'category': {feed}"
        assert feed['url'].startswith('http'), f"Feed URL should be http(s): {feed['url']}"
