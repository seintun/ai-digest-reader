"""Article scraping with fallback extraction and SQLite cache."""
from __future__ import annotations

import hashlib
import random
import sqlite3
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

import requests

USER_AGENT = "DailyDigestBot/1.0 (+https://dailydigest.vercel.app)"
CACHE_TTL_SECONDS = 24 * 60 * 60
CACHE_PATH = Path(".cache") / "scraper_cache.sqlite3"
REQUEST_TIMEOUT = 10
BACKOFF_SECONDS = (5, 15)
RATE_LIMIT_SECONDS = 2.5

_rate_lock = threading.Lock()
_last_request_at = 0.0


def _ensure_cache_db() -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(CACHE_PATH)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS article_cache (
                url_hash TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                content TEXT NOT NULL,
                scraped_at INTEGER NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def _hash_url(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def get_cached_content(url: str) -> Optional[str]:
    """Return cached content if younger than 24h."""
    _ensure_cache_db()
    conn = sqlite3.connect(CACHE_PATH)
    try:
        row = conn.execute(
            "SELECT content, scraped_at FROM article_cache WHERE url_hash = ?",
            (_hash_url(url),),
        ).fetchone()
        if not row:
            return None
        content, scraped_at = row
        if int(time.time()) - int(scraped_at) > CACHE_TTL_SECONDS:
            return None
        return content
    finally:
        conn.close()


def _set_cached_content(url: str, content: str) -> None:
    _ensure_cache_db()
    conn = sqlite3.connect(CACHE_PATH)
    try:
        conn.execute(
            """
            INSERT INTO article_cache (url_hash, url, content, scraped_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(url_hash) DO UPDATE SET
                content=excluded.content,
                scraped_at=excluded.scraped_at,
                url=excluded.url
            """,
            (_hash_url(url), url, content, int(time.time())),
        )
        conn.commit()
    finally:
        conn.close()


def _throttle() -> None:
    global _last_request_at
    with _rate_lock:
        now = time.time()
        jitter = random.uniform(-0.4, 0.4)
        wait_for = RATE_LIMIT_SECONDS + jitter - (now - _last_request_at)
        if wait_for > 0:
            time.sleep(wait_for)
        _last_request_at = time.time()


def _extract_with_trafilatura(html: str, url: str) -> Optional[str]:
    try:
        import trafilatura

        text = trafilatura.extract(
            html,
            url=url,
            include_links=False,
            include_images=False,
            favor_precision=True,
        )
        if text:
            return text.strip()
    except Exception:
        return None
    return None


def _extract_with_readability(html: str) -> Optional[str]:
    try:
        from readability import Document
        import trafilatura

        document = Document(html)
        article_html = document.summary()
        text = trafilatura.extract(
            article_html,
            include_links=False,
            include_images=False,
            favor_precision=False,
        )
        if text:
            return text.strip()
    except Exception:
        return None
    return None


def _fetch_and_extract(url: str) -> Optional[str]:
    headers = {"User-Agent": USER_AGENT}

    for attempt in range(1 + len(BACKOFF_SECONDS)):
        try:
            _throttle()
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            if response.status_code != 200 or not response.text:
                return None
            html = response.text
            text = _extract_with_trafilatura(html, url)
            if text:
                return text
            return _extract_with_readability(html)
        except requests.RequestException:
            if attempt < len(BACKOFF_SECONDS):
                time.sleep(BACKOFF_SECONDS[attempt])
            else:
                return None
    return None


def _scrape_one(url: str) -> Optional[str]:
    cached = get_cached_content(url)
    if cached:
        return cached
    extracted = _fetch_and_extract(url)
    if extracted:
        _set_cached_content(url, extracted)
    return extracted


def scrape_articles(urls: List[str], max_concurrent: int = 5) -> Dict[str, Optional[str]]:
    """Scrape articles with caching and fallbacks."""
    if not urls:
        return {}

    from concurrent.futures import ThreadPoolExecutor

    unique_urls = list(dict.fromkeys(urls))
    workers = max(1, min(max_concurrent, len(unique_urls)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        contents = list(pool.map(_scrape_one, unique_urls))
    return {url: content for url, content in zip(unique_urls, contents)}


def is_external_story_url(url: str) -> bool:
    """Return True for non-self-post URLs that are worth scraping."""
    if not url:
        return False
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    host = (parsed.netloc or "").lower()
    path = (parsed.path or "").lower()
    if "reddit.com" in host and "/comments/" in path:
        return False
    return True


def select_scrape_candidates(posts: List[Dict], limit: int = 40) -> List[Dict]:
    """Pick top scrape candidates from all sources."""
    filtered = []
    seen_urls = set()
    for post in sorted(posts, key=lambda p: (p.get("s", 0), p.get("c", 0)), reverse=True):
        score = int(post.get("s", 0) or 0)
        comments = int(post.get("c", 0) or 0)
        url = post.get("u", "")
        if score <= 10 and comments <= 5:
            continue
        if not is_external_story_url(url):
            continue
        if url in seen_urls:
            continue
        seen_urls.add(url)
        filtered.append(post)
        if len(filtered) >= limit:
            break
    return filtered
