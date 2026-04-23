"""Article scraping with fallback extraction and SQLite cache."""
from __future__ import annotations

import hashlib
import html
import json
import random
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests

import os as _os

from config import (
    HOST_BLOCK_TTL_SECONDS,
    RATE_LIMIT_SECONDS,
    REQUEST_TIMEOUT,
    SCRAPER_MAX_WORKERS,
)

USER_AGENT = "DailyDigestBot/1.0 (+https://dailydigest.vercel.app)"
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36 DailyDigestBot/1.0"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
}
JINA_PROXY_BASE = "https://r.jina.ai/"
JINA_TIMEOUT = float(_os.environ.get("SCRAPER_JINA_TIMEOUT", "8") or "8")
CACHE_TTL_SECONDS = 24 * 60 * 60
CACHE_PATH = Path(".cache") / "scraper_cache.sqlite3"
BACKOFF_SECONDS = (2, 5)

del _os

_blocked_hosts: Dict[str, float] = {}
_host_last_request: Dict[str, float] = {}
_host_lock = threading.Lock()


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
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_url_hash ON article_cache(url_hash)"
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


def _throttle(host: str = "") -> None:
    """Per-host rate limiting — different hosts can be fetched in parallel."""
    with _host_lock:
        now = time.time()
        jitter = random.uniform(-0.3, 0.3)
        last = _host_last_request.get(host, 0.0)
        wait_for = RATE_LIMIT_SECONDS + jitter - (now - last)
        _host_last_request[host] = now + max(0.0, wait_for)
    if wait_for > 0:
        time.sleep(wait_for)


def _is_host_temporarily_blocked(host: str) -> bool:
    if not host:
        return False
    with _host_lock:
        blocked_at = _blocked_hosts.get(host, 0.0)
        if not blocked_at:
            return False
        if time.time() - blocked_at > HOST_BLOCK_TTL_SECONDS:
            _blocked_hosts.pop(host, None)
            return False
        return True


def _mark_host_blocked(host: str) -> None:
    if not host:
        return
    with _host_lock:
        _blocked_hosts[host] = time.time()


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


def _extract_with_lxml_fallback(page_html: str) -> Optional[str]:
    try:
        from lxml import html as lxml_html

        doc = lxml_html.fromstring(page_html)
        text = " ".join(doc.xpath("//main//text()")) or doc.text_content()
        normalized = " ".join(text.split()).strip()
        if len(normalized) >= 140:
            return normalized
    except Exception:
        return None
    return None


def _extract_with_metadata_fallback(page_html: str) -> Optional[str]:
    try:
        from lxml import html as lxml_html

        doc = lxml_html.fromstring(page_html)

        # Prefer machine-readable metadata when article extraction fails.
        candidates: List[str] = []
        candidates.extend(doc.xpath("//meta[@property='og:description']/@content"))
        candidates.extend(doc.xpath("//meta[@name='description']/@content"))
        candidates.extend(doc.xpath("//meta[@name='twitter:description']/@content"))

        for raw in candidates:
            text = " ".join((raw or "").split()).strip()
            if len(text) >= 80:
                return text

        # Try JSON-LD articleBody/description fields as last resort.
        for script_body in doc.xpath("//script[@type='application/ld+json']/text()"):
            try:
                payload = json.loads(script_body)
            except Exception:
                continue
            items = payload if isinstance(payload, list) else [payload]
            for item in items:
                if not isinstance(item, dict):
                    continue
                article_body = item.get("articleBody")
                description = item.get("description")
                for raw in (article_body, description):
                    text = " ".join((raw or "").split()).strip()
                    if len(text) >= 80:
                        return text
    except Exception:
        return None
    return None


def _normalize_text(text: str, min_length: int = 80) -> Optional[str]:
    normalized = " ".join((text or "").split()).strip()
    if len(normalized) >= min_length:
        return normalized
    return None


def _fetch_via_jina_proxy(url: str) -> Tuple[Optional[str], str]:
    try:
        proxy_url = f"{JINA_PROXY_BASE}{url}"
        response = requests.get(
            proxy_url,
            headers={"User-Agent": USER_AGENT, "Accept": "text/plain, text/markdown, */*"},
            timeout=JINA_TIMEOUT,
        )
        status_code = int(response.status_code or 0)
        if status_code != 200:
            return None, f"jina_http_{status_code}"
        text = _normalize_text(response.text)
        if text:
            return text, ""
        return None, "jina_extract_failed"
    except requests.Timeout:
        return None, "jina_timeout"
    except requests.RequestException:
        return None, "jina_network_error"


def _fetch_and_extract(url: str) -> Tuple[Optional[str], str]:
    url = html.unescape(url or "").strip()
    if not url:
        return None, "invalid_url"
    host = (urlparse(url).netloc or "").lower()
    if _is_host_temporarily_blocked(host):
        return None, "host_blocked_skip"
    headers = REQUEST_HEADERS
    last_error = "unknown_error"

    for attempt in range(1 + len(BACKOFF_SECONDS)):
        try:
            _throttle(host)
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            status_code = int(response.status_code or 0)
            if status_code != 200 or not response.text:
                last_error = f"http_{status_code}"
                if status_code in {403, 429}:
                    _mark_host_blocked(host)
                    proxy_text, proxy_error = _fetch_via_jina_proxy(url)
                    if proxy_text:
                        return proxy_text, ""
                    last_error = f"{last_error}|{proxy_error}"
                if status_code in {403, 429, 500, 502, 503, 504} and attempt < len(BACKOFF_SECONDS):
                    time.sleep(BACKOFF_SECONDS[attempt])
                    continue
                return None, last_error
            content_type = (response.headers.get("Content-Type") or "").lower()
            if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
                return None, "unsupported_content_type"
            page_html = response.text
            lowered = page_html.lower()
            if any(token in lowered for token in ("cf-browser-verification", "just a moment...", "captcha", "access denied")):
                _mark_host_blocked(host)
                proxy_text, proxy_error = _fetch_via_jina_proxy(url)
                if proxy_text:
                    return proxy_text, ""
                return None, f"botwall_detected|{proxy_error}"
            text = _extract_with_trafilatura(page_html, url)
            if text:
                return text, ""
            fallback_text = _extract_with_readability(page_html)
            if fallback_text:
                return fallback_text, ""
            lxml_text = _extract_with_lxml_fallback(page_html)
            if lxml_text:
                return lxml_text, ""
            meta_text = _extract_with_metadata_fallback(page_html)
            if meta_text:
                return meta_text, ""
            proxy_text, proxy_error = _fetch_via_jina_proxy(url)
            if proxy_text:
                return proxy_text, ""
            return None, f"extract_failed|{proxy_error}"
        except requests.Timeout:
            last_error = "timeout"
            if attempt < len(BACKOFF_SECONDS):
                time.sleep(BACKOFF_SECONDS[attempt])
            else:
                proxy_text, proxy_error = _fetch_via_jina_proxy(url)
                if proxy_text:
                    return proxy_text, ""
                return None, f"{last_error}|{proxy_error}"
        except requests.RequestException:
            last_error = "network_error"
            if attempt < len(BACKOFF_SECONDS):
                time.sleep(BACKOFF_SECONDS[attempt])
            else:
                proxy_text, proxy_error = _fetch_via_jina_proxy(url)
                if proxy_text:
                    return proxy_text, ""
                return None, f"{last_error}|{proxy_error}"
    return None, last_error


def _scrape_one(url: str) -> Optional[str]:
    cached = get_cached_content(url)
    if cached:
        return cached
    extracted, _ = _fetch_and_extract(url)
    if extracted:
        _set_cached_content(url, extracted)
    return extracted


def _scrape_one_with_source(url: str) -> Tuple[Optional[str], str, str]:
    cached = get_cached_content(url)
    if cached:
        return cached, "cache", ""
    extracted, error = _fetch_and_extract(url)
    if extracted:
        _set_cached_content(url, extracted)
        return extracted, "network", ""
    return None, "failed", error


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


def scrape_articles_with_stats(
    urls: List[str],
    max_concurrent: int = 5,
    progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Tuple[Dict[str, Optional[str]], Dict[str, int]]:
    """Scrape articles and return content with cache/network outcome stats."""
    if not urls:
        return {}, {"requested": 0, "cache_hits": 0, "network_success": 0, "failures": 0}

    from concurrent.futures import ThreadPoolExecutor, as_completed

    unique_urls = list(dict.fromkeys(urls))
    workers = max(1, min(max_concurrent, len(unique_urls)))
    future_to_url = {}
    results_by_url: Dict[str, Tuple[Optional[str], str, str]] = {}
    cache_hits = 0
    network_success = 0
    failures = 0
    done = 0
    total = len(unique_urls)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        for url in unique_urls:
            future_to_url[pool.submit(_scrape_one_with_source, url)] = url

        for future in as_completed(future_to_url):
            url = future_to_url[future]
            content, source, error = future.result()
            results_by_url[url] = (content, source, error)
            done += 1
            if source == "cache":
                cache_hits += 1
            elif source == "network":
                network_success += 1
            else:
                failures += 1
            if progress_callback:
                progress_callback(
                    {
                        "done": done,
                        "total": total,
                        "status": source,
                        "url": url,
                        "error": error,
                        "cache_hits": cache_hits,
                        "network_success": network_success,
                        "failures": failures,
                    }
                )

    mapping = {url: results_by_url.get(url, (None, "failed", "missing_result"))[0] for url in unique_urls}
    stats = {
        "requested": len(unique_urls),
        "cache_hits": cache_hits,
        "network_success": network_success,
        "failures": failures,
    }
    return mapping, stats


def is_external_story_url(url: str) -> bool:
    """Return True for non-self-post URLs that are worth scraping."""
    if not url:
        return False
    parsed = urlparse(html.unescape(url))
    if parsed.scheme not in ("http", "https"):
        return False
    host = (parsed.netloc or "").lower()
    path = (parsed.path or "").lower()
    if host in {"i.redd.it", "v.redd.it", "preview.redd.it", "redditmedia.com"}:
        return False
    if path.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".mp4", ".mov", ".avi", ".m3u8")):
        return False
    if "reddit.com" in host and path.startswith("/live/"):
        return False
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
