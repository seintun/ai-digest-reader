import sqlite3
import time
from unittest.mock import MagicMock, patch  # noqa: F401

import scraper


def test_is_external_story_url_filters_reddit_self_posts():
    assert scraper.is_external_story_url("https://reddit.com/r/test/comments/abc123/foo") is False
    assert scraper.is_external_story_url("https://www.reddit.com/live/18hnzysb1elcs") is False
    assert scraper.is_external_story_url("https://i.redd.it/example.jpeg") is False
    assert scraper.is_external_story_url("https://v.redd.it/example") is False
    assert scraper.is_external_story_url("https://example.com/image.png") is False
    assert scraper.is_external_story_url("https://example.com/story") is True


def test_select_scrape_candidates_applies_threshold_dedup_and_limit():
    posts = [
        {"i": "rd-0", "u": "https://example.com/a", "s": 50, "c": 2},
        {"i": "rd-1", "u": "https://example.com/a", "s": 49, "c": 9},
        {"i": "hn-0", "u": "https://example.com/b", "s": 1, "c": 1},
        {"i": "rs-0", "u": "https://example.com/c", "s": 5, "c": 10},
        {"i": "rd-2", "u": "https://reddit.com/r/x/comments/y/z", "s": 200, "c": 200},
    ]
    picked = scraper.select_scrape_candidates(posts, limit=2)
    assert [p["u"] for p in picked] == ["https://example.com/a", "https://example.com/c"]


def test_get_cached_content_respects_ttl(tmp_path, monkeypatch):
    cache_path = tmp_path / "cache.sqlite3"
    monkeypatch.setattr(scraper, "CACHE_PATH", cache_path)

    scraper._ensure_cache_db()
    now = int(time.time())
    url = "https://example.com/story"
    url_hash = scraper._hash_url(url)
    conn = sqlite3.connect(cache_path)
    try:
        conn.execute(
            "INSERT INTO article_cache (url_hash, url, content, scraped_at) VALUES (?, ?, ?, ?)",
            (url_hash, url, "fresh content", now),
        )
        conn.commit()
    finally:
        conn.close()

    assert scraper.get_cached_content(url) == "fresh content"

    conn = sqlite3.connect(cache_path)
    try:
        conn.execute(
            "UPDATE article_cache SET scraped_at = ? WHERE url_hash = ?",
            (now - scraper.CACHE_TTL_SECONDS - 1, url_hash),
        )
        conn.commit()
    finally:
        conn.close()

    assert scraper.get_cached_content(url) is None


def test_scrape_articles_with_stats_uses_cache(tmp_path, monkeypatch):
    cache_path = tmp_path / "cache.sqlite3"
    monkeypatch.setattr(scraper, "CACHE_PATH", cache_path)
    monkeypatch.setattr(scraper, "_fetch_and_extract", lambda _url: ("network text", ""))

    url_cached = "https://example.com/cached"
    url_fresh = "https://example.com/fresh"
    scraper._set_cached_content(url_cached, "cached content")

    content, stats = scraper.scrape_articles_with_stats([url_cached, url_fresh], max_concurrent=1)
    assert content[url_cached] == "cached content"
    assert content[url_fresh] == "network text"
    assert stats["requested"] == 2
    assert stats["cache_hits"] == 1
    assert stats["network_success"] == 1
    assert stats["failures"] == 0


def test_scrape_articles_with_stats_emits_progress_events(monkeypatch):
    outcomes = {
        "https://example.com/a": ("a", "network", ""),
        "https://example.com/b": ("b", "cache", ""),
        "https://example.com/c": (None, "failed", "http_429"),
    }

    def fake_scrape(url):
        return outcomes[url]

    monkeypatch.setattr(scraper, "_scrape_one_with_source", fake_scrape)

    events = []
    content, stats = scraper.scrape_articles_with_stats(
        list(outcomes.keys()),
        max_concurrent=1,
        progress_callback=events.append,
    )

    assert len(events) == 3
    assert [event["done"] for event in events] == [1, 2, 3]
    assert [event["total"] for event in events] == [3, 3, 3]
    assert [event["status"] for event in events] == ["network", "cache", "failed"]
    assert events[-1]["error"] == "http_429"
    assert content["https://example.com/a"] == "a"
    assert content["https://example.com/b"] == "b"
    assert content["https://example.com/c"] is None
    assert stats["requested"] == 3
    assert stats["cache_hits"] == 1
    assert stats["network_success"] == 1
    assert stats["failures"] == 1


def test_fetch_via_archive_today_returns_text_on_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = (
        "<html><body><article>" + ("word " * 200) + "</article></body></html>"
    )
    with patch("scraper.requests.get", return_value=mock_response):
        with patch("scraper._extract_with_trafilatura", return_value="extracted text"):
            text, err = scraper._fetch_via_archive_today("https://www.cnbc.com/article/123")
    assert text == "extracted text"
    assert err == ""


def test_fetch_via_archive_today_returns_none_on_http_error():
    mock_response = MagicMock()
    mock_response.status_code = 404
    with patch("scraper.requests.get", return_value=mock_response):
        text, err = scraper._fetch_via_archive_today("https://www.cnbc.com/article/404")
    assert text is None
    assert "archive_http_404" in err


def test_fetch_via_archive_today_returns_none_on_timeout():
    import requests as req
    with patch("scraper.requests.get", side_effect=req.Timeout):
        text, err = scraper._fetch_via_archive_today("https://www.cnbc.com/article/slow")
    assert text is None
    assert err == "archive_timeout"
