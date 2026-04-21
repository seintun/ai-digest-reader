import sqlite3
import time

import scraper


def test_is_external_story_url_filters_reddit_self_posts():
    assert scraper.is_external_story_url("https://reddit.com/r/test/comments/abc123/foo") is False
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
    monkeypatch.setattr(scraper, "_fetch_and_extract", lambda _url: "network text")

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
