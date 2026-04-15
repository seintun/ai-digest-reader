#!/usr/bin/env python3
"""AI News Digest Aggregator - Main CLI."""
import argparse
import json
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Any

from config import SUBREDDITS, POST_LIMIT, DATE_FORMAT
from fetchers import fetch_reddit_posts, fetch_hn_posts
from formatter import format_digest

try:
    from analyzer import generate_summary
except ImportError:
    generate_summary = None


def normalize_posts(posts: List[Dict], prefix: str) -> List[Dict]:
    """Convert raw post data to v2 schema format with short keys."""
    normalized = []
    for i, post in enumerate(posts):
        normalized.append({
            "i": f"{prefix}-{i}",
            "t": post.get("title", ""),
            "u": post.get("url", ""),
            "s": post.get("score", 0),
            "c": post.get("comments", 0),
            "a": post.get("author", post.get("by", "")),
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
    
    reddit_normalized = normalize_posts(all_reddit_posts, "rd")
    hn_normalized = normalize_posts(hn_posts, "hn")
    
    summary = None
    if generate_summary and not args.no_ai:
        print("Generating AI summary with Claude...")
        summary = generate_summary(all_reddit_posts, hn_posts)
        if summary:
            print("AI summary generated successfully")
        else:
            print("AI summary unavailable, continuing without it")
    
    digest_date = date.today().strftime(DATE_FORMAT)
    digest_time = datetime.now().strftime("%H%M%S")
    
    digest = {
        "v": 2,
        "d": digest_date,
        "g": datetime.now().isoformat(),
        "r": reddit_normalized,
        "h": hn_normalized,
    }
    
    if summary:
        digest["summary"] = summary
    
    content = format_digest(all_reddit_posts, hn_posts, digest_date)
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
