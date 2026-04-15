#!/usr/bin/env python3
"""AI News Digest Aggregator - Main CLI."""
import argparse
from datetime import date, datetime
from pathlib import Path

from config import SUBREDDITS, POST_LIMIT, DATE_FORMAT
from fetchers import fetch_reddit_posts, fetch_hn_posts
from formatter import format_digest


def main():
    parser = argparse.ArgumentParser(description="AI News Digest Generator")
    parser.add_argument("--limit", type=int, default=POST_LIMIT, help="Posts per source")
    parser.add_argument("--output-dir", type=str, help="Output directory (default: output/YYYY-MM-DD)")
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
    digest_time = datetime.now().strftime("%H%M%S")
    content = format_digest(all_reddit_posts, hn_posts, digest_date)
    
    print("\n" + content)
    
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = Path("output") / digest_date
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"{digest_time}.md"
    output_path = output_dir / filename
    
    i = 1
    while output_path.exists():
        filename = f"{digest_time}_{i}.md"
        output_path = output_dir / filename
        i += 1
    
    output_path.write_text(content)
    print(f"\nSaved to {output_path}")


if __name__ == "__main__":
    main()