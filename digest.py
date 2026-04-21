#!/usr/bin/env python3
"""AI News Digest Aggregator - Main CLI."""
import argparse
import json
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List

from config import SUBREDDITS, POST_LIMIT, DATE_FORMAT
from fetchers import fetch_reddit_posts, fetch_hn_posts
from formatter import format_digest
from ranker import rank_posts
from scraper import scrape_articles, select_scrape_candidates

try:
    from config import SUBREDDIT_CATEGORIES, HN_CATEGORY, RSS_FEEDS
    from fetchers import fetch_all_rss_feeds
except ImportError:
    SUBREDDIT_CATEGORIES = {}
    HN_CATEGORY = "Tech"
    RSS_FEEDS = []
    fetch_all_rss_feeds = None

try:
    from analyzer import generate_summary
except ImportError:
    generate_summary = None

try:
    from analyzer_v2 import generate_summary as generate_summary_v2
except ImportError:
    generate_summary_v2 = None


def normalize_posts(posts: List[Dict], prefix: str, category: str = "") -> List[Dict]:
    """Convert raw post data to digest schema format with short keys."""
    normalized = []
    for i, post in enumerate(posts):
        normalized.append({
            "i": f"{prefix}-{i}",
            "t": post.get("title", ""),
            "u": post.get("url", ""),
            "p": post.get("permalink", ""),
            "b": post.get("body", ""),
            "s": post.get("score", 0),
            "c": post.get("comments", 0),
            "a": post.get("author", post.get("by", "")),
            "cat": post.get("category", "") or category,
            "ts": post.get("ts"),
        })
    return normalized


def main():
    parser = argparse.ArgumentParser(description="AI News Digest Generator")
    parser.add_argument("--limit", type=int, default=POST_LIMIT, help="Posts per source")
    parser.add_argument("--output-dir", type=str, help="Output directory (default: output/YYYY-MM-DD)")
    parser.add_argument("--subreddits", nargs="*", help="Specific subreddits to fetch")
    parser.add_argument("--no-ai", action="store_true", help="Skip AI summary generation")
    args = parser.parse_args()

    subreddits = args.subreddits if args.subreddits else SUBREDDITS

    print("Fetching Reddit posts...")
    all_reddit_posts = []
    for subreddit in subreddits:
        print(f"  - {subreddit}")
        posts = fetch_reddit_posts(subreddit, limit=args.limit)
        all_reddit_posts.extend(posts)

    print(f"Found {len(all_reddit_posts)} Reddit posts")

    print("Fetching Hacker News...")
    hn_posts = fetch_hn_posts(limit=args.limit)
    print(f"Found {len(hn_posts)} HN posts")

    # Tag each post with its subreddit category, then normalize in one pass
    for post in all_reddit_posts:
        sub = post.get("subreddit", "")
        post["category"] = SUBREDDIT_CATEGORIES.get(sub, "Tech")
    reddit_normalized = normalize_posts(all_reddit_posts, "rd")

    hn_normalized = normalize_posts(hn_posts, "hn", category=HN_CATEGORY)

    rss_posts = []
    if fetch_all_rss_feeds and RSS_FEEDS:
        print("Fetching RSS feeds...")
        rss_raw = fetch_all_rss_feeds(RSS_FEEDS, limit=args.limit)
        rss_posts = normalize_posts(rss_raw, "rs")
        print(f"Found {len(rss_posts)} RSS stories")

    all_posts = reddit_normalized + hn_normalized + rss_posts
    scraped_content = {}
    if all_posts:
        candidates = select_scrape_candidates(all_posts, limit=40)
        candidate_urls = [post.get("u", "") for post in candidates if post.get("u")]
        if candidate_urls:
            print(f"Scraping article content for {len(candidate_urls)} candidates...")
            scraped_content = scrape_articles(candidate_urls)

    ranked_posts = rank_posts(all_posts, scraped_content) if all_posts else []
    for post in ranked_posts:
        post["content"] = scraped_content.get(post.get("u", ""), "") or ""

    reddit_ranked = [post for post in ranked_posts if post.get("i", "").startswith("rd-")]
    hn_ranked = [post for post in ranked_posts if post.get("i", "").startswith("hn-")]
    rss_ranked = [post for post in ranked_posts if post.get("i", "").startswith("rs-")]

    summary = None
    if generate_summary_v2 and ranked_posts and not args.no_ai:
        print("Generating content-aware AI summary...")
        summary = generate_summary_v2(ranked_posts[:15])
        if summary:
            print("AI summary generated successfully")
        else:
            print("Content-aware summary unavailable, trying fallback summary...")

    if summary is None and generate_summary and not args.no_ai:
        summary = generate_summary(all_reddit_posts, hn_posts)
        if summary:
            print("Fallback AI summary generated")
        else:
            print("AI summary unavailable, continuing without it")

    digest_date = date.today().strftime(DATE_FORMAT)
    digest_time = datetime.now().strftime("%H%M%S")

    digest = {
        "v": 4,
        "d": digest_date,
        "g": datetime.now().isoformat(),
        "r": reddit_ranked,
        "h": hn_ranked,
        "rs": rss_ranked,
    }

    if summary:
        digest["summary"] = summary

    markdown_reddit = [
        {
            "title": post.get("t", ""),
            "url": post.get("u", ""),
            "score": post.get("s", 0),
            "subreddit": post.get("cat", ""),
        }
        for post in reddit_ranked
    ]
    markdown_hn = [
        {
            "title": post.get("t", ""),
            "url": post.get("u", ""),
            "score": post.get("s", 0),
        }
        for post in hn_ranked
    ]
    content = format_digest(markdown_reddit, markdown_hn, digest_date)
    print("\n" + content)

    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = Path("output") / digest_date

    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / "digest.json"
    with open(json_path, "w") as f:
        json.dump(digest, f, indent=2)
    print(f"\nSaved JSON to {json_path}")

    filename = f"digest-{digest_date}-{digest_time}.md"
    output_path = output_dir / filename

    i = 1
    while output_path.exists():
        filename = f"digest-{digest_date}-{digest_time}_{i}.md"
        output_path = output_dir / filename
        i += 1

    output_path.write_text(content)
    print(f"Saved markdown to {output_path}")


if __name__ == "__main__":
    main()
