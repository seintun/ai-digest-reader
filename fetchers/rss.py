"""RSS/Atom feed fetcher for DailyDigest."""
import re
import time
from typing import Dict, List
from urllib.parse import urlparse

import feedparser


def _strip_html(text: str) -> str:
    """Strip HTML tags and decode basic entities."""
    text = re.sub(r'<[^>]+>', '', text)
    text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace('&#39;', "'")
    return text.strip()


_PROMO_URL_PATHS = re.compile(
    r'/(?:gear|deals?|buying-guide|reviews?|coupons?|shop|affiliate)(?:/|$)|/best-',
    re.IGNORECASE,
)

_PROMO_TITLE_PATTERNS = re.compile(
    r'\bsponsored\b'
    r'|\bdeals?\b.*\$'
    r'|^\d+\s+best\b'
    r'|^the\s+\d+\s+best\b'
    r'|\b\d+%\s*off\b'
    r'|\bsave\s+\$'
    r'|\bbest\s+.{3,30}\s+(?:of|for|under|deals?)\b',
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

    Returns list of dicts with keys: title, url, permalink, body, score, comments, author, source_name, category
    Returns empty list on any error.
    """
    try:
        feed = feedparser.parse(feed_url, request_headers={'User-Agent': 'AIDigest/1.0'})
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
    """Fetch from multiple RSS feeds and return combined list.

    Args:
        feeds: List of dicts with keys: url, name, category
        limit: Max stories per feed

    Returns combined list of normalized posts from all feeds.
    """
    all_posts = []
    for feed_config in feeds:
        posts = fetch_rss_posts(
            feed_url=feed_config['url'],
            source_name=feed_config['name'],
            category=feed_config['category'],
            limit=limit,
        )
        all_posts.extend(posts)
    return all_posts
