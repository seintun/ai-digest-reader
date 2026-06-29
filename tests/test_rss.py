"""Tests for RSS feed fetcher (no network — unit tests only)."""
from unittest.mock import MagicMock, patch


class MockEntry(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError as exc:
            raise AttributeError(key) from exc


def make_mock_feed(entries):
    """Create a mock feedparser feed object."""
    feed = MagicMock()
    feed.entries = entries
    return feed


def make_entry(title="Test Title", link="https://example.com/story", summary="Body text here", author="Test Author"):
    return MockEntry(title=title, link=link, summary=summary, author=author)


def make_response(content=b"feed"):
    response = MagicMock()
    response.status_code = 200
    response.content = content
    return response


class TestFetchRssPosts:
    def test_returns_list(self):
        from fetchers.rss import fetch_rss_posts
        with patch('fetchers.rss.requests.get', return_value=make_response()), patch('feedparser.parse', return_value=make_mock_feed([make_entry()])):
            result = fetch_rss_posts("https://example.com/feed", "Test", "Tech")
        assert isinstance(result, list)

    def test_normalizes_fields(self):
        from fetchers.rss import fetch_rss_posts
        entry = make_entry(title="My Title", link="https://x.com/a", summary="Body", author="Alice")
        with patch('fetchers.rss.requests.get', return_value=make_response()), patch('feedparser.parse', return_value=make_mock_feed([entry])):
            result = fetch_rss_posts("https://example.com/feed", "TechCrunch", "Tech")
        assert len(result) == 1
        post = result[0]
        assert post['title'] == "My Title"
        assert post['url'] == "https://x.com/a"
        assert post['source_name'] == "TechCrunch"
        assert post['category'] == "Tech"
        assert post['score'] == 0
        assert post['comments'] == 0

    def test_strips_html_from_body(self):
        from fetchers.rss import fetch_rss_posts
        entry = make_entry(summary="<p>Hello <b>world</b></p>")
        with patch('fetchers.rss.requests.get', return_value=make_response()), patch('feedparser.parse', return_value=make_mock_feed([entry])):
            result = fetch_rss_posts("https://example.com/feed", "Source", "Tech")
        assert '<' not in result[0]['body']
        assert 'Hello' in result[0]['body']

    def test_returns_empty_on_request_exception(self):
        from fetchers.rss import fetch_rss_posts
        with patch('fetchers.rss.requests.get', side_effect=Exception("Network error")):
            result = fetch_rss_posts("https://bad.com/feed", "Bad", "Tech")
        assert result == []

    def test_returns_empty_on_parse_exception(self):
        from fetchers.rss import fetch_rss_posts
        with patch('fetchers.rss.requests.get', return_value=make_response()), patch('feedparser.parse', side_effect=Exception("Parse error")):
            result = fetch_rss_posts("https://bad.com/feed", "Bad", "Tech")
        assert result == []

    def test_returns_empty_on_http_error(self):
        from fetchers.rss import fetch_rss_posts
        response = make_response()
        response.status_code = 403
        with patch('fetchers.rss.requests.get', return_value=response), patch('feedparser.parse') as parse:
            result = fetch_rss_posts("https://bad.com/feed", "Bad", "Tech")
        assert result == []
        parse.assert_not_called()

    def test_respects_limit(self):
        from fetchers.rss import fetch_rss_posts
        entries = [make_entry(title=f"Story {i}") for i in range(20)]
        with patch('fetchers.rss.requests.get', return_value=make_response()), patch('feedparser.parse', return_value=make_mock_feed(entries)):
            result = fetch_rss_posts("https://example.com/feed", "Source", "Tech", limit=5)
        assert len(result) == 5

    def test_body_truncated_to_280(self):
        from fetchers.rss import fetch_rss_posts
        long_body = "word " * 100  # 500 chars
        entry = make_entry(summary=long_body)
        with patch('fetchers.rss.requests.get', return_value=make_response()), patch('feedparser.parse', return_value=make_mock_feed([entry])):
            result = fetch_rss_posts("https://example.com/feed", "Source", "Tech")
        assert len(result[0]['body']) <= 280


class TestFetchAllRssFeeds:
    def test_combines_multiple_feeds(self):
        from fetchers.rss import fetch_all_rss_feeds
        feeds = [
            {"url": "https://a.com/feed", "name": "A", "category": "Tech"},
            {"url": "https://b.com/feed", "name": "B", "category": "AI & ML"},
        ]
        with patch('fetchers.rss.fetch_rss_posts', return_value=[{'title': 'x'}]):
            result = fetch_all_rss_feeds(feeds)
        assert len(result) == 2  # 1 post per feed

    def test_returns_empty_for_no_feeds(self):
        from fetchers.rss import fetch_all_rss_feeds
        assert fetch_all_rss_feeds([]) == []
