from config import SUBREDDITS, HN_API_URL, POST_LIMIT

def test_subreddits_configured():
    assert isinstance(SUBREDDITS, list)
    assert len(SUBREDDITS) > 0

def test_hn_configured():
    assert isinstance(HN_API_URL, str)
    assert POST_LIMIT == 10
