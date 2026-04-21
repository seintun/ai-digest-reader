# RSS Feed Fetcher

## Overview
`fetchers/rss.py` provides RSS/Atom feed parsing for DailyDigest, expanding news coverage beyond Reddit and HN.

## Design Decisions
- **feedparser library**: Industry-standard RSS/Atom parser, handles malformed feeds gracefully
- **Graceful degradation**: Any per-feed failure returns empty list, pipeline continues
- **HTML stripping**: Summaries are stripped to plain text (news sites embed HTML in RSS bodies)
- **Unified interface**: Same normalized dict shape as Reddit/HN fetchers — title, url, permalink, body, score, comments, author
- **score=0, comments=0**: RSS has no voting/comment metadata; frontend ranking handles this gracefully

## Data Flow
config.RSS_FEEDS → fetch_all_rss_feeds() → [fetch_rss_posts() per feed] → normalized story dicts → digest.py normalize_posts()

## Adding New Feeds
Add a dict to `RSS_FEEDS` in `config.py`:
```python
{"url": "https://example.com/feed.xml", "name": "Display Name", "category": "Tech"}
```
Categories: "AI & ML", "Tech", "Science", "World News", "Futurology", "Startups"
