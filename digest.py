#!/usr/bin/env python3
"""AI News Digest Aggregator - Main CLI."""
import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from pathlib import Path
import time
from typing import Any, Dict, List

from config import SUBREDDITS, POST_LIMIT, DATE_FORMAT
from fetchers import fetch_reddit_posts, fetch_hn_posts
from formatter import format_digest
from pipeline_metrics import (
    render_dashboard,
)
from ranker import rank_posts_with_metrics
from scraper import scrape_articles_with_stats, select_scrape_candidates
from model_pricing import usage_to_dict
from engine.config import load_engine_config, render_preflight
from engine.openclaw import generate_summary_with_openclaw

try:
    from config import SUBREDDIT_CATEGORIES, HN_CATEGORY, RSS_FEEDS
    from fetchers import fetch_all_rss_feeds
except ImportError:
    SUBREDDIT_CATEGORIES = {}
    HN_CATEGORY = "Tech"
    RSS_FEEDS = []
    fetch_all_rss_feeds = None

try:
    from analyzer_v2 import generate_summary as generate_summary_v2
except ImportError:
    generate_summary_v2 = None

try:
    from analyzer_v2 import generate_summary_with_meta
except ImportError:
    generate_summary_with_meta = None


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
            "sn": post.get("source_name", ""),
            "cat": post.get("category", "") or category,
            "ts": post.get("ts"),
        })
    return normalized


def main():
    run_started = time.perf_counter()
    parser = argparse.ArgumentParser(description="AI News Digest Generator")
    parser.add_argument("--limit", type=int, default=POST_LIMIT, help="Posts per source")
    parser.add_argument("--output-dir", type=str, help="Output directory (default: output/YYYY-MM-DD)")
    parser.add_argument("--subreddits", nargs="*", help="Specific subreddits to fetch")
    parser.add_argument("--no-ai", action="store_true", help="Skip AI summary generation")
    args = parser.parse_args()
    engine_config = load_engine_config()
    print(render_preflight(engine_config))

    subreddits = args.subreddits if args.subreddits else SUBREDDITS

    REDDIT_CACHE_PATH = Path("reddit-cache.json")

    print("Fetching Reddit posts...")
    fetch_started = time.perf_counter()
    all_reddit_posts = []

    def _fetch_subreddit(subreddit: str) -> List[Dict]:
        posts = fetch_reddit_posts(subreddit, limit=args.limit)
        print(f"  - {subreddit} ({len(posts)} posts)")
        return posts

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(_fetch_subreddit, sub): sub for sub in subreddits}
        for future in as_completed(futures):
            all_reddit_posts.extend(future.result())

    if all_reddit_posts:
        # Save cache for CI environments where Reddit is blocked
        try:
            REDDIT_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(REDDIT_CACHE_PATH, "w") as f:
                json.dump(all_reddit_posts, f)
            print(f"Found {len(all_reddit_posts)} Reddit posts (cache updated)")
        except Exception as e:
            print(f"Found {len(all_reddit_posts)} Reddit posts (cache write failed: {e})")
    else:
        # Reddit blocked (common in CI) — use last known good cache
        if REDDIT_CACHE_PATH.exists():
            try:
                with open(REDDIT_CACHE_PATH) as f:
                    all_reddit_posts = json.load(f)
                print(f"Found 0 live Reddit posts — using cache ({len(all_reddit_posts)} posts)")
            except Exception as e:
                print(f"Found 0 Reddit posts (cache read failed: {e})")
        else:
            print("Found 0 Reddit posts (no cache available)")

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
    fetch_seconds = time.perf_counter() - fetch_started

    all_posts = reddit_normalized + hn_normalized + rss_posts
    scraped_content = {}
    scrape_stats = {"requested": 0, "cache_hits": 0, "network_success": 0, "failures": 0}
    scrape_started = time.perf_counter()
    if all_posts:
        candidates = select_scrape_candidates(all_posts, limit=40)
        candidate_urls = [post.get("u", "") for post in candidates if post.get("u")]
        if candidate_urls:
            print(f"Scraping article content for {len(candidate_urls)} candidates...")
            scrape_error_counts: Dict[str, int] = {}

            def _on_scrape_progress(event: Dict[str, Any]) -> None:
                done = int(event.get("done", 0) or 0)
                total = int(event.get("total", 0) or 0)
                status = str(event.get("status", "") or "")
                url = str(event.get("url", "") or "")
                error = str(event.get("error", "") or "")
                cache_hits = int(event.get("cache_hits", 0) or 0)
                network_success = int(event.get("network_success", 0) or 0)
                failures = int(event.get("failures", 0) or 0)
                percent = (done / total * 100.0) if total else 0.0
                line = (
                    f"\r  progress: {done}/{total} ({percent:5.1f}%)"
                    f" | cache={cache_hits} network={network_success} failed={failures}"
                )
                print(line, end="", flush=True)
                if status == "failed":
                    reason = error or "unknown_error"
                    scrape_error_counts[reason] = scrape_error_counts.get(reason, 0) + 1
                    print(f"\n  failed: {url} ({reason})")
                if done == total:
                    print("")

            scraped_content, scrape_stats = scrape_articles_with_stats(
                candidate_urls,
                progress_callback=_on_scrape_progress,
            )
            if scrape_error_counts:
                reason_summary = ", ".join(
                    f"{reason}={count}" for reason, count in sorted(scrape_error_counts.items())
                )
                print(f"  scrape failures by reason: {reason_summary}")
    scrape_seconds = time.perf_counter() - scrape_started

    print("Scraping complete.")
    print(f"Ranking {len(all_posts)} stories (LLM quality scoring)...")
    ranking_started = time.perf_counter()
    ranked_posts = []
    ranking_metrics = {"total_posts": 0, "llm_quality_used": False}
    if all_posts:
        ranked_posts, ranking_metrics = rank_posts_with_metrics(all_posts, scraped_content)
    ranking_seconds = time.perf_counter() - ranking_started
    for post in ranked_posts:
        post["content"] = scraped_content.get(post.get("u", ""), "") or ""

    reddit_ranked = [post for post in ranked_posts if post.get("i", "").startswith("rd-")]
    hn_ranked = [post for post in ranked_posts if post.get("i", "").startswith("hn-")]
    rss_ranked = [post for post in ranked_posts if post.get("i", "").startswith("rs-")]

    summary = None
    summary_meta = {"source": "none", "generated": False, "usage": usage_to_dict(0, 0)}
    summary_started = time.perf_counter()
    if ranked_posts and not args.no_ai and engine_config.uses_openclaw_summary:
        print("Generating AI summary via OpenClaw engine...")
        summary, summary_meta = generate_summary_with_openclaw(ranked_posts[:15], engine_config)
        if summary:
            print("OpenClaw AI summary generated successfully")
        elif engine_config.openclaw_on_failure == "fail-no-deploy":
            raise RuntimeError(f"OpenClaw summary unavailable: {summary_meta.get('error', 'unknown error')}")
    elif generate_summary_with_meta and ranked_posts and not args.no_ai:
        print("Generating content-aware AI summary...")
        summary, summary_meta = generate_summary_with_meta(ranked_posts[:15])
        if summary:
            print("AI summary generated successfully")
        else:
            print("Content-aware summary unavailable, trying fallback summary...")
    elif generate_summary_v2 and ranked_posts and not args.no_ai:
        summary = generate_summary_v2(ranked_posts[:15])
        summary_meta = {"source": "openrouter_or_cli", "generated": bool(summary)}

    if summary is None and not args.no_ai:
        print("AI summary unavailable, continuing without it")
        summary_meta = {"source": "none", "generated": False, "usage": summary_meta.get("usage", usage_to_dict(0, 0))}
    summary_seconds = time.perf_counter() - summary_started

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

    scrape_requested = scrape_stats.get("requested", 0)
    scrape_success = scrape_stats.get("cache_hits", 0) + scrape_stats.get("network_success", 0)
    scrape_success_rate = (scrape_success / scrape_requested * 100.0) if scrape_requested else 0.0
    cache_hit_rate = (scrape_stats.get("cache_hits", 0) / scrape_requested * 100.0) if scrape_requested else 0.0

    ranking_usage = ranking_metrics.get("llm_usage", {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0})
    summary_usage = summary_meta.get("usage", {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0})
    session_model_cost = round(float(ranking_usage.get("cost_usd", 0.0)) + float(summary_usage.get("cost_usd", 0.0)), 6)
    ranking_cost_source = str(ranking_usage.get("cost_source", "unavailable"))
    summary_cost_source = str(summary_usage.get("cost_source", "unavailable"))
    openrouter_cost_used = "openrouter_usage" in {ranking_cost_source, summary_cost_source} or "mixed_openrouter_and_estimate" in {ranking_cost_source, summary_cost_source}
    cost_sources = sorted({ranking_cost_source, summary_cost_source})
    if openrouter_cost_used:
        pricing_source = "OpenRouter response usage accounting (`usage.cost`, credits treated as USD-equivalent)"
    else:
        pricing_source = "No OpenRouter reported cost for this run"

    total_seconds = time.perf_counter() - run_started
    metrics = {
        "runtime": {
            "fetch_seconds": round(fetch_seconds, 2),
            "scrape_seconds": round(scrape_seconds, 2),
            "ranking_seconds": round(ranking_seconds, 2),
            "summary_seconds": round(summary_seconds, 2),
            "total_seconds": round(total_seconds, 2),
            "within_budget": total_seconds < 180,
        },
        "scraping": {
            "candidate_urls": scrape_requested,
            "cache_hits": scrape_stats.get("cache_hits", 0),
            "network_success": scrape_stats.get("network_success", 0),
            "failures": scrape_stats.get("failures", 0),
            "success_rate": round(scrape_success_rate, 1),
            "cache_hit_rate": round(cache_hit_rate, 1),
        },
        "ranking": ranking_metrics,
        "summary": summary_meta,
        "cost": {
            "pricing_source": pricing_source,
            "cost_sources": cost_sources,
            "openrouter_cost_used": openrouter_cost_used,
            "session_model_usd": session_model_cost,
            "ranking_llm": ranking_usage,
            "summary_llm": summary_usage,
            "within_budget": session_model_cost < 0.25,
        },
        "engine": {
            "name": engine_config.engine,
            "profile": engine_config.openclaw_profile if engine_config.engine == "openclaw" else None,
            "stages": list(engine_config.openclaw_stages),
            "credential_source": "openclaw_explicit" if engine_config.engine == "openclaw" else "project_env_or_none",
            "failure_policy": engine_config.openclaw_on_failure if engine_config.engine == "openclaw" else "standalone default",
        },
        "degradation": {
            "scraping_fallback_used": scrape_stats.get("failures", 0) > 0,
            "ranking_fallback_used": not ranking_metrics.get("llm_quality_used", False),
            "summary_fallback_used": summary_meta.get("source") == "analyzer_v1",
            "no_summary_fallback_used": not summary_meta.get("generated", False),
        },
    }
    digest["metrics"] = metrics

    print("Pipeline metrics:")
    print(f"  - runtime: {metrics['runtime']['total_seconds']}s")
    print(f"  - scrape success: {metrics['scraping']['success_rate']}%")
    print(f"  - cache hit rate: {metrics['scraping']['cache_hit_rate']}%")
    print(f"  - ranking LLM used: {metrics['ranking']['llm_quality_used']}")
    print(f"  - summary source: {metrics['summary']['source']}")
    print(f"  - session model cost: ${metrics['cost']['session_model_usd']}")

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

    # NotebookLM ingestion stage (post-processing)
    notebook_ingest_result = None
    if engine_config.engine == "openclaw" and "notebooklm_ingest" in engine_config.openclaw_stages:
        print("[NotebookLM Ingestion] Starting ingestion of digest links...")
        from engine.openclaw import ingest_digest_into_notebooklm
        dry_run = os.environ.get("AI_DIGEST_NOTEBOOK_DRY_RUN") == "1"
        notebook_ingest_result = ingest_digest_into_notebooklm(digest, engine_config, dry_run=dry_run)
        added = notebook_ingest_result.get("added", notebook_ingest_result.get("applied", 0))
        skipped = len(notebook_ingest_result.get("to_skip", [])) + notebook_ingest_result.get("deferred_count", 0)
        failed = notebook_ingest_result.get("failed_count", 0)
        dry_run_flag = notebook_ingest_result.get("dry_run", False)
        status = "(dry run)" if dry_run_flag else ""
        print(f"NotebookLM ingestion: added={added} skipped={skipped} failed={failed} {status}")
        if notebook_ingest_result.get("notebook_url"):
            print(f"Notebook: {notebook_ingest_result['notebook_url']}")
        # Append notebook info into digest metrics
        digest.setdefault("metrics", {})["notebook_ingest"] = {
            "enabled": True,
            "added": added,
            "skipped": skipped,
            "failed": failed,
            "dry_run": dry_run_flag,
            "notebook_id": notebook_ingest_result.get("notebook_id"),
            "notebook_url": notebook_ingest_result.get("notebook_url"),
            "error": notebook_ingest_result.get("error"),
        }
    else:
        digest.setdefault("metrics", {})["notebook_ingest"] = {"enabled": False}

    json_path = output_dir / "digest.json"
    with open(json_path, "w") as f:
        json.dump(digest, f, indent=2)
    print(f"\nSaved JSON to {json_path}")

    # Write ingestion report if stage ran
    if notebook_ingest_result is not None:
        ingest_report_path = output_dir / "notebooklm-ingest.json"
        ingest_report_path.write_text(json.dumps(notebook_ingest_result, indent=2), encoding="utf-8")
        print(f"Saved ingestion report to {ingest_report_path}")

    metrics_path = output_dir / "metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"Saved metrics to {metrics_path}")

    dashboard_path = output_dir / "monitoring-dashboard.md"
    dashboard_path.write_text(render_dashboard(metrics))
    print(f"Saved dashboard to {dashboard_path}")

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
