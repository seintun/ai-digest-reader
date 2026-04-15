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
    parser.add_argument("--subreddits", nargs="*", help="Specific subreddits to fetch")
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
    
    digest_date = date.today().strftime(DATE_FORMAT)
    content = format_digest(all_reddit_posts, hn_posts, digest_date)
    
    print("\n" + content)
    
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content)
        print(f"\nSaved to {output_path}")


if __name__ == "__main__":
    main()