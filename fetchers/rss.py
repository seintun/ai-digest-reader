"""RSS/Atom feed fetcher for DailyDigest."""
from __future__ import annotations

import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List
from urllib.parse import urlparse

import feedparser
import requests


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)) or default)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)) or default)
    except ValueError:
        return default


def _rss_timeout() -> tuple[float, float]:
    return (
        _env_float("RSS_CONNECT_TIMEOUT", 1.5),
        _env_float("RSS_READ_TIMEOUT", 5.0),
    )


def _rss_headers() -> dict[str, str]:
    return {"User-Agent": os.environ.get("RSS_USER_AGENT", os.environ.get("REDDIT_USER_AGENT", "AIDigest/1.0"))}


def _strip_html(text: str) -> str:
    """Strip HTML tags and decode basic entities."""
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace('&#39;', "'")
    return text.strip()


_PROMO_URL_PATHS = re.compile(
    r'/(?:gear|deals?|buying-guide|reviews?|coupons?|shop|affiliate|promo)(?:/|$)|/best-',
    re.IGNORECASE,
)

_PROMO_TITLE_PATTERNS = re.compile(
    r'\bsponsored\b'
    r'|^\d+\s+best\b'
    r'|^the\s+\d+\s+best\b'
    r'|\b\d+%\s*off\b'
    r'|\bsave\s+\$'
    r'|\bbest\s+.{3,30}\s+(?:of|for|under|deals?)\b'
    r'|\bpromo\s*codes?\b'
    r'|\bcoupon\s*codes?\b'
    r'|\$\d[\d,.]*\s*off\b',
    re.IGNORECASE,
)


def _is_promotional(title: str, url: str) -> bool:
    path = urlparse(url).path
    if _PROMO_URL_PATHS.search(path):
        return True
    if _PROMO_TITLE_PATTERNS.search(title):
        return True
    return False


def fetch_rss_posts(feed_url: str, source_name: str, category: str, limit: int = 10) -> List[Dict]:
    """Fetch and normalize posts from an RSS/Atom feed.

    Returns list of dicts with keys: title, url, permalink, body, score,
    comments, author, source_name, category. Returns empty list on any error.
    Network is fetched with explicit connect/read timeouts before parsing so one
    slow feed cannot stall the whole digest.
    """
    try:
        response = requests.get(feed_url, headers=_rss_headers(), timeout=_rss_timeout())
        status_code = int(response.status_code or 0)
        if status_code != 200:
            print(f"RSS fetch HTTP {status_code} for {source_name} ({feed_url})")
            return []
        feed = feedparser.parse(response.content)
        posts = []
        for entry in feed.entries[:limit * 3]:
            title = _strip_html(getattr(entry, 'title', '') or '')
            url = getattr(entry, 'link', '') or ''
            if _is_promotional(title, url):
                continue
            body_raw = getattr(entry, 'summary', '') or getattr(entry, 'description', '') or ''
            body = _strip_html(body_raw)[:280]
            author = getattr(entry, 'author', '') or ''
            ts_struct = getattr(entry, 'published_parsed', None) or getattr(entry, 'updated_parsed', None)
            try:
                ts = int(time.mktime(ts_struct)) if ts_struct else None
            except (TypeError, ValueError):
                ts = None
            posts.append({
                'title': title,
                'url': url,
                'permalink': url,
                'body': body,
                'score': 0,
                'comments': 0,
                'author': author,
                'source_name': source_name,
                'category': category,
                'ts': ts,
            })
            if len(posts) >= limit:
                break
        return posts
    except Exception as e:
        print(f"RSS fetch error for {source_name} ({feed_url}): {e}")
        return []


def fetch_all_rss_feeds(feeds: List[Dict], limit: int = 10) -> List[Dict]:
    """Fetch from multiple RSS feeds and return combined list."""
    if not feeds:
        return []

    all_posts = []
    workers = max(1, min(_env_int("RSS_MAX_WORKERS", 8), len(feeds)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_to_feed = {
            pool.submit(
                fetch_rss_posts,
                feed_config['url'],
                feed_config['name'],
                feed_config['category'],
                limit,
            ): feed_config
            for feed_config in feeds
        }
        for future in as_completed(future_to_feed):
            feed_config = future_to_feed[future]
            try:
                all_posts.extend(future.result())
            except Exception as exc:
                print(f"RSS fetch worker error for {feed_config.get('name', 'unknown')}: {exc}")
    return all_posts
