"""Reddit fetcher with fast terminal-error handling.

Reddit often blocks unauthenticated JSON/RSS requests with 401/403/429 from
servers and CI. Treat those as terminal by default so digest runs fail fast and
fall back to the local Reddit cache instead of wasting time on duplicate
endpoints and RSS fallback attempts.
"""
from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Iterable

import feedparser
import requests

from config import POST_LIMIT

TERMINAL_REDDIT_STATUSES = {401, 403, 429}
_BLOCK_CACHE_LOCK = threading.Lock()


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off", ""}


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


def _reddit_headers() -> dict[str, str]:
    return {"User-Agent": os.environ.get("REDDIT_USER_AGENT", "AIDigest/1.0")}


def _reddit_timeout() -> tuple[float, float]:
    return (
        _env_float("REDDIT_CONNECT_TIMEOUT", 1.5),
        _env_float("REDDIT_READ_TIMEOUT", 3.0),
    )


def _block_cache_path() -> Path:
    return Path(os.environ.get("REDDIT_BLOCK_CACHE_PATH", "output/reddit-blocks.json"))


def _global_block_ttl_seconds() -> int:
    return max(0, _env_int("REDDIT_GLOBAL_BLOCK_TTL_SECONDS", 6 * 60 * 60))


def _subreddit_block_ttl_seconds() -> int:
    return max(0, _env_int("REDDIT_SUBREDDIT_BLOCK_TTL_SECONDS", 6 * 60 * 60))


def _read_block_cache() -> dict:
    path = _block_cache_path()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_block_cache(payload: dict) -> None:
    path = _block_cache_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        print(f"Reddit block cache write failed: {exc}")


def _write_global_block_cache(reason: str, status_code: int | None = None) -> None:
    ttl = _global_block_ttl_seconds()
    if ttl <= 0:
        return
    with _BLOCK_CACHE_LOCK:
        now = time.time()
        payload = _read_block_cache()
        payload["global"] = {
            "blocked_until_epoch": now + ttl,
            "updated_at_epoch": now,
            "reason": reason,
            "status_code": status_code,
        }
        _write_block_cache(payload)


def _write_subreddit_block_cache(subreddit: str, status_code: int) -> None:
    ttl = _subreddit_block_ttl_seconds()
    if ttl <= 0:
        return
    with _BLOCK_CACHE_LOCK:
        now = time.time()
        payload = _read_block_cache()
        subreddits = payload.setdefault("subreddits", {})
        if not isinstance(subreddits, dict):
            subreddits = {}
            payload["subreddits"] = subreddits
        subreddits[subreddit] = {
            "blocked_until_epoch": now + ttl,
            "updated_at_epoch": now,
            "reason": "terminal_http_status",
            "status_code": status_code,
        }
        _write_block_cache(payload)


def _global_block_cache_active() -> bool:
    payload = _read_block_cache()
    # Backward compatible with old flat cache shape.
    global_payload = payload.get("global", payload)
    if not isinstance(global_payload, dict):
        return False
    try:
        blocked_until = float(global_payload.get("blocked_until_epoch", 0) or 0)
    except (ValueError, TypeError):
        return False
    if blocked_until > time.time():
        remaining = int(blocked_until - time.time())
        print(f"Reddit live fetch skipped: global block cache active ({remaining}s remaining)")
        return True
    return False


def _subreddit_block_cache_active(subreddit: str, verbose: bool = True) -> bool:
    payload = _read_block_cache()
    subreddits = payload.get("subreddits", {})
    if not isinstance(subreddits, dict):
        return False
    entry = subreddits.get(subreddit)
    if not isinstance(entry, dict):
        return False
    try:
        blocked_until = float(entry.get("blocked_until_epoch", 0) or 0)
    except (ValueError, TypeError):
        return False
    if blocked_until > time.time():
        if verbose:
            status_code = entry.get("status_code", "unknown")
            remaining = int(blocked_until - time.time())
            print(f"Reddit live fetch skipped for r/{subreddit}: cached terminal {status_code} ({remaining}s remaining)")
        return True
    return False


def _extract_post_list(data: dict, limit: int) -> list[dict]:
    if "data" in data:
        data_section = data["data"]
        if isinstance(data_section, list):
            return data_section[:limit]
        if isinstance(data_section, dict) and "children" in data_section:
            children = data_section.get("children", [])
            return [c.get("data", {}) for c in children[:limit]]
        return []

    if "children" in data:
        return [child.get("data", {}) for child in data.get("children", [])[:limit]]

    return []


def _normalize_reddit_post(post: dict, subreddit: str) -> dict:
    permalink = f"https://reddit.com{post.get('permalink', '')}"
    return {
        "title": post.get("title", ""),
        "url": post.get("url", permalink),
        "permalink": permalink,
        "body": post.get("selftext", "")[:280].replace("\n", " ").strip(),
        "score": post.get("score", 0),
        "subreddit": post.get("subreddit", subreddit),
        "author": post.get("author", ""),
        "comments": post.get("num_comments", 0),
        "ts": post.get("created_utc"),
    }


def _fetch_reddit_rss_posts(subreddit: str, limit: int, headers: dict[str, str]) -> list[dict]:
    posts: list[dict] = []
    rss_url = f"https://www.reddit.com/r/{subreddit}/hot.rss?limit={limit}"
    try:
        response = requests.get(rss_url, headers=headers, timeout=_reddit_timeout())
        if response.status_code != 200:
            print(f"Reddit RSS fallback {response.status_code} for r/{subreddit}: {rss_url}")
            return []
        feed = feedparser.parse(response.content)
        for entry in feed.entries[:limit]:
            permalink = getattr(entry, "link", "")
            posts.append({
                "title": entry.get("title", ""),
                "url": permalink,
                "permalink": permalink,
                "body": "",
                "score": 0,
                "subreddit": subreddit,
                "author": "",
                "comments": 0,
                "ts": None,
            })
        if not posts:
            print(f"Reddit RSS fallback also empty for r/{subreddit}")
    except Exception as exc:
        print(f"Reddit RSS fallback error for r/{subreddit}: {exc}")
    return posts[:limit]


def fetch_reddit_posts(subreddit: str, limit: int = POST_LIMIT) -> list[dict]:
    """Fetch top posts from a subreddit.

    Uses JSON API first. 401/403/429 are terminal by default: they return []
    immediately to let the caller use cache instead of trying top.json and RSS.
    Set REDDIT_RSS_FALLBACK_ON_TERMINAL=1 to keep the old RSS fallback behavior
    for terminal statuses.
    """
    posts: list[dict] = []
    headers = _reddit_headers()

    if _subreddit_block_cache_active(subreddit):
        return []

    for url_template in [
        "https://www.reddit.com/r/{}/hot.json?limit={}",
        "https://www.reddit.com/r/{}/top.json?limit={}&t=day",
    ]:
        url = url_template.format(subreddit, limit)
        try:
            response = requests.get(url, headers=headers, timeout=_reddit_timeout())
            status_code = int(response.status_code or 0)
            if status_code in TERMINAL_REDDIT_STATUSES:
                print(f"Reddit JSON {status_code} for r/{subreddit}: {url} (terminal; skipping remaining endpoints)")
                _write_subreddit_block_cache(subreddit, status_code)
                if _env_bool("REDDIT_RSS_FALLBACK_ON_TERMINAL", False):
                    return _fetch_reddit_rss_posts(subreddit, limit, headers)
                return []
            if status_code != 200:
                print(f"Reddit JSON {status_code} for r/{subreddit}: {url}")
                continue
            data = response.json()
            post_list = _extract_post_list(data, limit)
            for post in post_list:
                posts.append(_normalize_reddit_post(post, subreddit))
                if len(posts) >= limit:
                    break
            if posts:
                break
        except (requests.RequestException, ValueError) as exc:
            print(f"Reddit JSON error for r/{subreddit}: {exc}")
            continue

    if posts:
        return posts[:limit]

    # RSS fallback for non-terminal JSON failures/empty responses.
    return _fetch_reddit_rss_posts(subreddit, limit, headers)


def _probe_reddit_status(subreddit: str) -> int | None:
    url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit=1"
    try:
        response = requests.get(url, headers=_reddit_headers(), timeout=_reddit_timeout())
        return int(response.status_code or 0)
    except requests.RequestException as exc:
        print(f"Reddit probe error for r/{subreddit}: {exc}")
        return None


def reddit_live_fetch_globally_blocked(subreddits: Iterable[str]) -> bool:
    """Return True when a quick Reddit probe shows global terminal blocking.

    This keeps full digest runs from launching dozens of doomed subreddit
    requests. The block result is cached for REDDIT_GLOBAL_BLOCK_TTL_SECONDS
    (default 6h) under output/reddit-blocks.json.
    """
    if not _env_bool("REDDIT_GLOBAL_BLOCK_PROBE", True):
        return False
    if _global_block_cache_active():
        return True

    probe_count = max(1, _env_int("REDDIT_GLOBAL_PROBE_COUNT", 4))
    probe_subs = [
        subreddit
        for subreddit in dict.fromkeys(subreddits)
        if not _subreddit_block_cache_active(subreddit, verbose=False)
    ][:probe_count]
    if not probe_subs:
        return False

    threshold = max(1, _env_int("REDDIT_GLOBAL_BLOCK_THRESHOLD", min(3, len(probe_subs))))
    terminal_count = 0
    terminal_status: int | None = None

    for subreddit in probe_subs:
        status_code = _probe_reddit_status(subreddit)
        if status_code in TERMINAL_REDDIT_STATUSES:
            terminal_count += 1
            terminal_status = status_code
            print(f"Reddit probe terminal {status_code} for r/{subreddit} ({terminal_count}/{threshold})")
            if terminal_count >= threshold:
                print("Reddit appears globally blocked; skipping live Reddit fetch and using cache if available")
                _write_global_block_cache("terminal_http_status_threshold", terminal_status)
                return True
        elif status_code == 200:
            print(f"Reddit probe OK for r/{subreddit}; proceeding with live Reddit fetch")
            return False
        elif status_code is not None:
            print(f"Reddit probe non-terminal {status_code} for r/{subreddit}; proceeding with live Reddit fetch")
            return False

    return False
