from config import SUBREDDITS, HN_API_URL, POST_LIMIT

def test_subreddits_configured():
    assert isinstance(SUBREDDITS, list)
    assert len(SUBREDDITS) > 0

def test_hn_configured():
    assert isinstance(HN_API_URL, str)
    assert POST_LIMIT == 10


def test_subreddit_categories_is_dict():
    from config import SUBREDDIT_CATEGORIES
    assert isinstance(SUBREDDIT_CATEGORIES, dict)
    assert len(SUBREDDIT_CATEGORIES) >= 10


def test_subreddit_categories_covers_all_subreddits():
    from config import SUBREDDITS, SUBREDDIT_CATEGORIES
    for sub in SUBREDDITS:
        assert sub in SUBREDDIT_CATEGORIES, f"Missing category for r/{sub}"


def test_hn_category_is_string():
    from config import HN_CATEGORY
    assert isinstance(HN_CATEGORY, str)
    assert HN_CATEGORY  # not empty


def test_rss_feeds_is_list():
    from config import RSS_FEEDS
    assert isinstance(RSS_FEEDS, list)
    assert len(RSS_FEEDS) >= 5


def test_rss_feeds_have_required_keys():
    from config import RSS_FEEDS
    for feed in RSS_FEEDS:
        assert 'url' in feed, f"Feed missing 'url': {feed}"
        assert 'name' in feed, f"Feed missing 'name': {feed}"
        assert 'category' in feed, f"Feed missing 'category': {feed}"
        assert feed['url'].startswith('http'), f"Feed URL should be http(s): {feed['url']}"
