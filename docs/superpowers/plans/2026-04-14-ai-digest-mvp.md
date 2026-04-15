# AI News Digest Aggregator - MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A CLI script that fetches top AI posts from Reddit + Hacker News and outputs a markdown digest for daily reading.

**Architecture:** Single Python script (`digest.py`) with modular fetchers. Uses public JSON APIs. No external dependencies beyond `requests`.

**Tech Stack:** Python 3.10+, `requests` library

---

## File Structure

```
dailydiget/
├── digest.py           # Main CLI script
├── config.py          # Configuration (sources, subreddits)
├── fetchers/
│   ├── __init__.py
│   ├── reddit.py      # Reddit API fetcher
│   └── hn.py         # Hacker News API fetcher
├── formatter.py       # Markdown formatter
├── main.py            # Entry point
├── requirements.txt   # Python dependencies
└── README.md         # Usage instructions
```

---

## Task 1: Project Setup

**Files:**
- Create: `dailydiget/requirements.txt`
- Create: `dailydiget/README.md`

- [ ] **Step 1: Create requirements.txt**

```
requests>=2.28.0
```

- [ ] **Step 2: Create README.md**

```markdown
# AI News Digest Aggregator

Quick daily digest of hot AI content from Reddit + Hacker News.

## Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Generate today's digest
python digest.py

# With Obsidian sync (future)
python digest.py --obsidian
```

## Sources
- Reddit: r/ArtificialIntelligence, r/LocalLLaMA, r/ChatGPT, r/MachineLearning
- Hacker News: Front page
```

- [ ] **Step 3: Install dependencies**

```bash
pip install -r dailydiget/requirements.txt
```

- [ ] **Step 4: Commit**

```bash
git add dailydiget/requirements.txt dailydiget/README.md
git commit -m "chore: initial project setup"
```

---

## Task 2: Configuration Module

**Files:**
- Create: `dailydiget/config.py`

- [ ] **Step 2: Write failing test**

```python
# tests/test_config.py
import sys
sys.path.insert(0, 'dailydiget')
from config import SUBREDDITS, HN_TOP_IDS, POST_LIMIT

def test_subreddits_configured():
    assert isinstance(SUBREDDITS, list)
    assert len(SUBREDDITS) > 0

def test_hn_configured():
    assert isinstance(HN_TOP_IDS, str)
    assert POST_LIMIT == 10
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL - module not found

- [ ] **Step 4: Write config.py**

```python
"""Configuration for AI News Digest Aggregator."""

SUBREDDITS = [
    "ArtificialIntelligence",
    "LocalLLaMA",
    "ChatGPT",
    "MachineLearning",
]

HN_API_URL = "https://hacker-news.firebase.io/v0"

POST_LIMIT = 10

DATE_FORMAT = "%Y-%m-%d"
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add dailydiget/config.py tests/test_config.py
git commit -m "feat: add configuration module"
```

---

## Task 3: Reddit Fetcher

**Files:**
- Create: `dailydiget/fetchers/__init__.py`
- Create: `dailydiget/fetchers/reddit.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_reddit.py
import sys
sys.path.insert(0, 'dailydiget')
from fetchers.reddit import fetch_reddit_posts

def test_fetch_returns_list():
    posts = fetch_reddit_posts("ArtificialIntelligence", limit=5)
    assert isinstance(posts, list)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_reddit.py::test_fetch_returns_list -v`
Expected: FAIL - module not found

- [ ] **Step 3: Write fetchers/__init__.py**

```python
"""Fetchers package."""
from .reddit import fetch_reddit_posts
from .hn import fetch_hn_posts

__all__ = ["fetch_reddit_posts", "fetch_hn_posts"]
```

- [ ] **Step 4: Write reddit.py**

```python
"""Reddit API fetcher."""
import requests
from config import SUBREDDITS, POST_LIMIT


def fetch_reddit_posts(subreddit: str, limit: int = POST_LIMIT) -> list[dict]:
    """Fetch top posts from a subreddit."""
    url = f"https://www.reddit.com/r/{subreddit}/.json?limit={limit}"
    headers = {"User-Agent": "AIDigest/1.0"}
    
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    
    data = response.json()
    posts = []
    
    for child in data["data"]["children"]:
        post = child["data"]
        posts.append({
            "title": post.get("title", ""),
            "url": f"https://reddit.com{post.get('permalink', '')}",
            "score": post.get("score", 0),
            "subreddit": post.get("subreddit", subreddit),
            "author": post.get("author", ""),
            "comments": post.get("num_comments", 0),
        })
    
    return posts
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_reddit.py::test_fetch_returns_list -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add dailydiget/fetchers/__init__.py dailydiget/fetchers/reddit.py tests/test_reddit.py
git commit -m "feat: add Reddit fetcher"
```

---

## Task 4: Hacker News Fetcher

**Files:**
- Create: `dailydiget/fetchers/hn.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_hn.py
import sys
sys.path.insert(0, 'dailydiget')
from fetchers.hn import fetch_hn_posts

def test_fetch_returns_list():
    posts = fetch_hn_posts(limit=5)
    assert isinstance(posts, list)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_hn.py::test_fetch_returns_list -v`
Expected: FAIL - module not found

- [ ] **Step 3: Write hn.py**

```python
"""Hacker News API fetcher."""
import requests
from config import HN_API_URL, POST_LIMIT


def fetch_hn_posts(limit: int = POST_LIMIT) -> list[dict]:
    """Fetch top stories from Hacker News."""
    top_stories_url = f"{HN_API_URL}/topstories.json"
    
    response = requests.get(top_stories_url, timeout=10)
    response.raise_for_status()
    
    story_ids = response.json()[:limit]
    posts = []
    
    for story_id in story_ids:
        item_url = f"{HN_API_URL}/item/{story_id}.json"
        item_response = requests.get(item_url, timeout=10)
        
        if item_response.status_code == 200:
            story = item_response.json()
            if story and story.get("url"):
                posts.append({
                    "title": story.get("title", ""),
                    "url": story.get("url", ""),
                    "score": story.get("score", 0),
                    "author": story.get("by", ""),
                    "comments": story.get("descendants", 0),
                })
    
    return posts
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_hn.py::test_fetch_returns_list -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add dailydiget/fetchers/hn.py tests/test_hn.py
git commit -m "feat: add Hacker News fetcher"
```

---

## Task 5: Markdown Formatter

**Files:**
- Create: `dailydiget/formatter.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_formatter.py
import sys
sys.path.insert(0, 'dailydiget')
from formatter import format_digest

def test_format_creates_markdown():
    reddit_posts = [
        {"title": "Test Post", "url": "https://reddit.com", "score": 100, "subreddit": "ai"}
    ]
    content = format_digest(reddit_posts, [], "2026-04-14")
    assert "# AI Digest" in content
    assert "Test Post" in content
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_formatter.py::test_format_creates_markdown -v`
Expected: FAIL - module not found

- [ ] **Step 3: Write formatter.py**

```python
"""Markdown formatter for digest output."""
from datetime import date


def format_digest(reddit_posts: list, hn_posts: list, digest_date: str) -> str:
    """Format posts into markdown digest."""
    lines = [
        f"# AI Digest - {digest_date}",
        "",
        "## Reddit",
        "",
    ]
    
    for i, post in enumerate(reddit_posts, 1):
        lines.append(f"{i}. **{post['title']}**")
        lines.append(f"   - [{post['subreddit']}]({post['url']}) | {post['score']} points")
        lines.append("")
    
    lines.extend([
        "## Hacker News",
        "",
    ])
    
    for i, post in enumerate(hn_posts, 1):
        lines.append(f"{i}. **{post['title']}**")
        lines.append(f"   - [{post['url']}]({post['score']}) | {post['score']} points")
        lines.append("")
    
    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_formatter.py::test_format_creates_markdown -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add dailydiget/formatter.py tests/test_formatter.py
git commit -m "feat: add markdown formatter"
```

---

## Task 6: Main CLI Entry Point

**Files:**
- Create: `dailydiget/digest.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_main.py
import sys
import io
sys.path.insert(0, 'dailydiget')
from digest import main

def test_main_runs(monkeypatch):
    # Mock the fetchers to return empty to avoid network calls
    import fetchers.reddit
    import fetchers.hn
    monkeypatch.setattr(fetchers.reddit, "fetch_reddit_posts", lambda *a, **k: [])
    monkeypatch.setattr(fetchers.hn, "fetch_hn_posts", lambda *a, **k: [])
    main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_main.py::test_main_runs -v`
Expected: FAIL - module not found

- [ ] **Step 3: Write digest.py**

```python
#!/usr/bin/env python3
"""AI News Digest Aggregator - Main CLI."""
import argparse
from datetime import date
from pathlib import Path

from config import SUBREDDITS, POST_LIMIT, DATE_FORMAT
from fetchers import fetch_reddit_posts, fetch_hn_posts
from formatter import format_digest


def main():
    parser = argparse.ArgumentParser(description="AI News Digest Generator")
    parser.add_argument("--limit", type=int, default=POST_LIMIT, help="Posts per source")
    parser.add_argument("--output", type=str, help="Output file path")
    args = parser.parse_args()
    
    print("Fetching Reddit posts...")
    all_reddit_posts = []
    for subreddit in SUBREDDITS:
        posts = fetch_reddit_posts(subreddit, limit=args.limit)
        all_reddit_posts.extend(posts)
    
    print("Fetching Hacker News...")
    hn_posts = fetch_hn_posts(limit=args.limit)
    
    digest_date = date.today().strftime(DATE_FORMAT)
    content = format_digest(all_reddit_posts, hn_posts, digest_date)
    
    print(content)
    
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content)
        print(f"\nSaved to {output_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_main.py::test_main_runs -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add dailydiget/digest.py tests/test_main.py
git commit -m "feat: add main CLI entry point"
```

---

## Task 7: Integration Test

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: Write integration test**

```python
# tests/test_integration.py
import sys
sys.path.insert(0, 'dailydiget')

def test_full_digest_generation():
    """Test the full pipeline works."""
    from fetchers import fetch_reddit_posts, fetch_hn_posts
    from formatter import format_digest
    from datetime import date
    
    # This will make real network calls - skip if offline
    reddit = fetch_reddit_posts("ArtificialIntelligence", limit=3)
    hn = fetch_hn_posts(limit=3)
    
    digest = format_digest(reddit, hn, date.today().strftime("%Y-%m-%d"))
    
    assert "AI Digest" in digest
    assert len(digest) > 100
```

- [ ] **Step 2: Run integration test**

```bash
python -m pytest tests/test_integration.py -v
```
Expected: PASS (or SKIP if network unavailable)

- [ ] **Step 3: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: add integration test"
```

---

## Execution Summary

**Total tasks:** 7
**Estimated time:** 45-60 minutes (TDD, small commits)

**Approach:**
- Task 1: Setup (5 min)
- Task 2: Config (5 min)
- Task 3: Reddit fetcher (10 min)
- Task 4: HN fetcher (10 min)
- Task 5: Formatter (5 min)
- Task 6: CLI (10 min)
- Task 7: Integration test (10 min)

---

**Plan complete and saved to `docs/superpowers/plans/2026-04-14-ai-digest-mvp.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**