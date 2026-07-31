"""Tests for extraction-stage telemetry (which extractor won, and why others failed)."""
from unittest.mock import MagicMock

import scraper


def _html_ok():
    resp = MagicMock()
    resp.status_code = 200
    resp.text = "<html><body>" + ("word " * 200) + "</body></html>"
    resp.headers = {"Content-Type": "text/html"}
    return resp


def test_fetch_and_extract_records_defuddle_win(monkeypatch):
    monkeypatch.setattr(scraper, "_is_host_temporarily_blocked", lambda host: False)
    monkeypatch.setattr(scraper, "_extract_with_defuddle", lambda url: "defuddle content")
    text, error, tele = scraper._fetch_and_extract("https://example.com/a")
    assert text == "defuddle content"
    assert tele["winner"] == "defuddle"
    # Nothing downstream was attempted.
    assert tele["attempts"] == ["defuddle"]


def test_fetch_and_extract_records_fallthrough_to_trafilatura(monkeypatch):
    """defuddle fails -> requests fetch -> trafilatura wins; telemetry records the fallthrough + reason."""
    monkeypatch.setattr(scraper, "_is_host_temporarily_blocked", lambda host: False)
    monkeypatch.setattr(scraper, "_extract_with_defuddle", lambda url: None)
    monkeypatch.setattr(scraper, "_throttle", lambda host="": None)
    monkeypatch.setattr(scraper.requests, "get", lambda *a, **k: _html_ok())
    monkeypatch.setattr(scraper, "_extract_with_trafilatura", lambda html, url: "traf text")

    text, error, tele = scraper._fetch_and_extract("https://example.com/a")
    assert text == "traf text"
    assert tele["winner"] == "trafilatura"
    assert "defuddle" in tele["failures"]  # defuddle was tried and failed
    assert "fetch" not in tele["failures"]  # the HTTP fetch succeeded


def test_fetch_and_extract_records_all_failures(monkeypatch):
    """When every extractor fails, telemetry lists each attempted stage with a reason."""
    monkeypatch.setattr(scraper, "_is_host_temporarily_blocked", lambda host: False)
    monkeypatch.setattr(scraper, "_extract_with_defuddle", lambda url: None)
    monkeypatch.setattr(scraper, "_throttle", lambda host="": None)
    resp = MagicMock()
    resp.status_code = 403
    resp.text = ""
    resp.headers = {}
    monkeypatch.setattr(scraper.requests, "get", lambda *a, **k: resp)
    monkeypatch.setattr(scraper, "_fetch_via_jina_proxy", lambda url: (None, "jina_http_403"))
    monkeypatch.setattr(scraper, "_fetch_via_archive_today", lambda url: (None, "archive_http_404"))
    monkeypatch.setattr(scraper, "BACKOFF_SECONDS", ())

    text, error, tele = scraper._fetch_and_extract("https://example.com/a")
    assert text is None
    assert tele["winner"] is None
    assert "defuddle" in tele["failures"]
    # The fetch stage recorded the HTTP status reason.
    assert any("403" in r for r in tele["failures"].values())


def test_scrape_articles_with_stats_aggregates_extractor_breakdown(monkeypatch, tmp_path):
    """scrape_articles_with_stats rolls per-URL telemetry into an extractor_breakdown."""
    monkeypatch.setattr(scraper, "CACHE_PATH", tmp_path / "cache.sqlite3")

    def fake_scrape(url):
        if url.endswith("/a"):
            return "content a", "network", "", {"winner": "defuddle", "attempts": ["defuddle"], "failures": {}}
        if url.endswith("/b"):
            return "content b", "network", "", {"winner": "trafilatura", "attempts": ["defuddle", "fetch", "trafilatura"], "failures": {"defuddle": "no_output"}}
        return None, "failed", "http_403", {"winner": None, "attempts": ["defuddle", "fetch"], "failures": {"defuddle": "no_output", "fetch": "http_403"}}

    monkeypatch.setattr(scraper, "_scrape_one_with_source", fake_scrape)
    content, stats = scraper.scrape_articles_with_stats(
        ["https://x.com/a", "https://x.com/b", "https://x.com/c"], max_concurrent=1
    )
    breakdown = stats["extractor_breakdown"]
    assert breakdown["defuddle"] == 1
    assert breakdown["trafilatura"] == 1
    assert breakdown["none"] == 1
    # Failure-reason counts aggregate across URLs.
    assert breakdown["failure_reasons"]["defuddle:no_output"] == 2
