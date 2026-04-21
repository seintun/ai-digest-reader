"""Multi-signal ranking for digest stories."""
from __future__ import annotations

import json
import math
import os
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

from model_pricing import usage_to_dict

QUALITY_MAX_RETRIES = int(os.environ.get("RANKER_AI_MAX_RETRIES", "0") or "0")
QUALITY_RETRY_SECONDS = (2, 5)
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "moonshotai/kimi-k2.6")
RANKER_AI_CONNECT_TIMEOUT = float(os.environ.get("RANKER_AI_CONNECT_TIMEOUT", "10") or "10")
RANKER_AI_READ_TIMEOUT = float(os.environ.get("RANKER_AI_READ_TIMEOUT", "12") or "12")


def _source_from_id(story_id: str) -> str:
    return (story_id or "").split("-", 1)[0]


def _path_signature(url: str) -> Tuple[str, str]:
    parsed = urlparse(url or "")
    domain = (parsed.netloc or "").lower()
    path = re.sub(r"/+", "/", (parsed.path or "/")).rstrip("/") or "/"
    return domain, path


def _are_same_story(url_a: str, url_b: str) -> bool:
    domain_a, path_a = _path_signature(url_a)
    domain_b, path_b = _path_signature(url_b)
    if not domain_a or domain_a != domain_b:
        return False
    ratio = SequenceMatcher(None, path_a, path_b).ratio()
    return ratio >= 0.8


def _compute_cross_source_scores(posts: List[Dict]) -> Dict[str, float]:
    scores: Dict[str, float] = {}
    for post in posts:
        story_id = post.get("i", "")
        url = post.get("u", "")
        sources = {_source_from_id(story_id)}
        for other in posts:
            if other is post:
                continue
            if _are_same_story(url, other.get("u", "")):
                sources.add(_source_from_id(other.get("i", "")))
        points = min(15.0, 5.0 * max(0, len(sources) - 1))
        scores[story_id] = points
    return scores


def _recency_points(post: Dict) -> float:
    now = datetime.now(timezone.utc).timestamp()
    ts = post.get("ts")
    if ts is None:
        hours_ago = 24.0
    else:
        try:
            hours_ago = max(0.0, (now - float(ts)) / 3600.0)
        except (TypeError, ValueError):
            hours_ago = 24.0
    return 15.0 * math.exp(-hours_ago / 24.0)


def _engagement_points(post: Dict) -> float:
    score = float(post.get("s", 0) or 0)
    comments = float(post.get("c", 0) or 0)
    normalized_score = min(score / 5000.0, 1.0) * 20.0
    normalized_comments = min(comments / 1000.0, 1.0) * 20.0
    return normalized_score + normalized_comments


def _heuristic_quality(post: Dict, scraped_content: Dict[str, str]) -> int:
    content = scraped_content.get(post.get("u", ""), "") or ""
    excerpt = content[:200].strip() or (post.get("b", "") or "")[:200].strip()
    if not excerpt:
        return 1
    if len(excerpt) > 170:
        return 7
    if len(excerpt) > 100:
        return 5
    return 3


def _parse_json_object(text: str) -> Optional[dict]:
    stripped = (text or "").strip()
    if not stripped:
        return None
    if stripped.startswith("```"):
        chunks = [part.strip() for part in stripped.split("```") if part.strip()]
        for chunk in chunks:
            if chunk.startswith("json"):
                chunk = chunk[4:].strip()
            if chunk.startswith("{"):
                stripped = chunk
                break
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        if start == -1:
            return None
        try:
            return json.loads(stripped[start:])
        except json.JSONDecodeError:
            return None


def _quality_candidates(posts: List[Dict], scraped_content: Dict[str, str]) -> List[Tuple[str, str]]:
    candidates: List[Tuple[str, str]] = []
    for post in posts:
        content = scraped_content.get(post.get("u", ""), "") or ""
        excerpt = content[:200].strip()
        if excerpt:
            candidates.append((post.get("i", ""), excerpt))
    return candidates


def _quality_prompt(candidates: List[Tuple[str, str]]) -> str:
    lines = [
        "Rate each excerpt for substance from 1 (clickbait/thin) to 10 (highly substantive).",
        "Output only JSON object in this exact format: {\"ratings\": [{\"id\": \"rd-0\", \"rating\": 7}]}",
    ]
    for story_id, excerpt in candidates:
        lines.append(f"[{story_id}] {excerpt}")
    return "\n".join(lines)


def _request_quality_ratings(candidates: List[Tuple[str, str]]) -> Tuple[Optional[Dict[str, int]], Dict[str, float | int | str]]:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key or not candidates:
        return None, usage_to_dict(0, 0)
    prompt = _quality_prompt(candidates)

    input_tokens = 0
    output_tokens = 0
    usage_payload = usage_to_dict(0, 0)
    raw = ""
    last_error = ""
    retries = max(0, min(QUALITY_MAX_RETRIES, len(QUALITY_RETRY_SECONDS)))
    for attempt in range(1 + retries):
        try:
            body = json.dumps(
                {
                    "model": OPENROUTER_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                }
            )
            max_time = max(1, int(RANKER_AI_CONNECT_TIMEOUT + RANKER_AI_READ_TIMEOUT))
            result = subprocess.run(
                [
                    "curl",
                    "-sS",
                    "--max-time",
                    str(max_time),
                    "-X",
                    "POST",
                    "https://openrouter.ai/api/v1/chat/completions",
                    "-H",
                    f"Authorization: Bearer {api_key}",
                    "-H",
                    "Content-Type: application/json",
                    "-H",
                    "HTTP-Referer: https://dailydigest.vercel.app",
                    "-H",
                    "X-Title: DailyDigest",
                    "--data",
                    body,
                ],
                capture_output=True,
                text=True,
                timeout=max_time + 3,
            )
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or f"curl_exit_{result.returncode}")
            payload = json.loads(result.stdout or "{}")
            if payload.get("error"):
                raise RuntimeError(str(payload.get("error")))
            choices = payload.get("choices", [])
            raw = ((choices[0] or {}).get("message") or {}).get("content") if choices else ""
            usage = payload.get("usage", {}) or {}
            # Keep token accounting simple and explicit.
            input_tokens = int(usage.get("prompt_tokens", 0) or 0)
            output_tokens = int(usage.get("completion_tokens", 0) or 0)
            usage_payload = usage_to_dict(
                input_tokens,
                output_tokens,
                openrouter_usage=usage,
                cost_source="openrouter_usage",
            )
            usage_payload["total_tokens"] = int(usage.get("total_tokens", input_tokens + output_tokens) or (input_tokens + output_tokens))
            break
        except Exception as exc:
            last_error = str(exc)
            is_retryable = any(token in last_error.lower() for token in ("429", "rate", "timeout", "503", "504"))
            if attempt < retries and is_retryable:
                print(f"Ranking AI batch retry {attempt + 1}/{retries} after error: {exc}")
                time.sleep(QUALITY_RETRY_SECONDS[attempt])
                continue
            print(f"Ranking AI batch failed: {exc}")
            return None, usage_payload

    if not raw:
        if last_error:
            print(f"Ranking AI batch empty response after retries: {last_error}")
        return None, usage_payload

    parsed = _parse_json_object(raw)
    if not parsed:
        return None, usage_payload
    items = parsed.get("ratings")
    if not isinstance(items, list):
        return None, usage_payload

    ratings: Dict[str, int] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        story_id = item.get("id")
        rating = item.get("rating")
        if not isinstance(story_id, str):
            continue
        try:
            rating_int = int(rating)
        except (TypeError, ValueError):
            continue
        ratings[story_id] = max(1, min(10, rating_int))
    return ratings or None, usage_payload


def _chunk_candidates(items: List[Tuple[str, str]], chunks: int) -> List[List[Tuple[str, str]]]:
    if not items:
        return []
    bucket_count = max(1, min(chunks, len(items)))
    size = math.ceil(len(items) / bucket_count)
    return [items[i:i + size] for i in range(0, len(items), size)]


def _estimate_quality_cost_usd(candidates: List[Tuple[str, str]], workers: int) -> float:
    base_input = sum(max(1, len(excerpt) // 4) for _, excerpt in candidates)
    batch_count = max(1, min(workers, len(candidates)))
    overhead_input = batch_count * 60
    estimated_input_tokens = base_input + overhead_input
    estimated_output_tokens = max(20 * batch_count, 6 * len(candidates))
    # Generic budget estimate: configurable and model-agnostic (no model-specific hardcoded rates).
    usd_per_1k_tokens = float(os.environ.get("RANKER_AI_ESTIMATE_USD_PER_1K_TOKENS", "0.01") or "0.01")
    estimated_total_tokens = estimated_input_tokens + estimated_output_tokens
    return round((estimated_total_tokens / 1000.0) * usd_per_1k_tokens, 6)


def _rate_content_quality(posts: List[Dict], scraped_content: Dict[str, str]) -> Tuple[Optional[Dict[str, int]], Dict[str, float | int | str]]:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        usage = usage_to_dict(0, 0)
        usage.update({
            "ai_parallel_enabled": False,
            "ai_parallel_workers": 0,
            "ai_batches": 0,
            "ai_parallel_fallback_reason": "missing_api_key",
        })
        return None, usage

    candidates = _quality_candidates(posts, scraped_content)
    if not candidates:
        usage = usage_to_dict(0, 0)
        usage.update({
            "ai_parallel_enabled": False,
            "ai_parallel_workers": 0,
            "ai_batches": 0,
            "ai_parallel_fallback_reason": "no_candidates",
        })
        return None, usage

    configured_workers = int(os.environ.get("RANKER_AI_PARALLEL_WORKERS", "4") or "4")
    configured_workers = max(1, min(configured_workers, 8))
    max_usd = float(os.environ.get("RANKER_AI_PARALLEL_MAX_USD", "0.12") or "0.12")
    projected_usd = _estimate_quality_cost_usd(candidates, configured_workers)

    fallback_reason = ""
    workers = configured_workers
    if workers > 1 and projected_usd > max_usd:
        workers = 1
        fallback_reason = "projected_cost_exceeded"

    batches = _chunk_candidates(candidates, workers)
    ratings: Dict[str, int] = {}
    input_tokens = 0
    output_tokens = 0
    summed_cost_usd = 0.0
    saw_provider_cost = False
    saw_estimated_cost = False
    batch_count = len(batches)

    if workers == 1:
        batch_ratings, usage = _request_quality_ratings(batches[0])
        input_tokens += int(usage.get("input_tokens", 0) or 0)
        output_tokens += int(usage.get("output_tokens", 0) or 0)
        summed_cost_usd += float(usage.get("cost_usd", 0.0) or 0.0)
        if usage.get("cost_source") == "openrouter_usage" and usage.get("openrouter_reported_cost_credits") is not None:
            saw_provider_cost = True
        else:
            saw_estimated_cost = True
        if batch_ratings:
            ratings.update(batch_ratings)
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(_request_quality_ratings, batch) for batch in batches]
            for future in as_completed(futures):
                batch_ratings, usage = future.result()
                input_tokens += int(usage.get("input_tokens", 0) or 0)
                output_tokens += int(usage.get("output_tokens", 0) or 0)
                summed_cost_usd += float(usage.get("cost_usd", 0.0) or 0.0)
                if usage.get("cost_source") == "openrouter_usage" and usage.get("openrouter_reported_cost_credits") is not None:
                    saw_provider_cost = True
                else:
                    saw_estimated_cost = True
                if batch_ratings:
                    ratings.update(batch_ratings)

    if saw_provider_cost and saw_estimated_cost:
        cost_source = "mixed_openrouter_and_estimate"
    elif saw_provider_cost:
        cost_source = "openrouter_usage"
    else:
        cost_source = "static_pricing_estimate"
    usage = usage_to_dict(
        input_tokens,
        output_tokens,
        openrouter_usage={"cost": summed_cost_usd},
        cost_source=cost_source,
    )
    usage["total_tokens"] = input_tokens + output_tokens
    usage.update({
        "ai_parallel_enabled": workers > 1,
        "ai_parallel_workers": workers,
        "ai_batches": batch_count,
        "ai_parallel_fallback_reason": fallback_reason,
    })
    return ratings or None, usage


def rank_posts_with_metrics(posts: List[Dict], scraped_content: Dict[str, str]) -> Tuple[List[Dict], Dict]:
    """Score and rank posts with rank/content metadata and ranking metrics."""
    ranked = [post.copy() if isinstance(post, dict) else dict(post) for post in posts]
    cross_source_scores = _compute_cross_source_scores(ranked)
    llm_quality, llm_usage = _rate_content_quality(ranked, scraped_content)

    for post in ranked:
        story_id = post.get("i", "")
        engagement = _engagement_points(post)
        recency = _recency_points(post)
        cross_source = cross_source_scores.get(story_id, 0.0)

        content = scraped_content.get(post.get("u", ""), "") or ""
        if llm_quality is None:
            quality_rating = 0
            quality_points = 0.0
        else:
            quality_rating = llm_quality.get(story_id, _heuristic_quality(post, scraped_content))
            quality_points = (quality_rating / 10.0) * 30.0

        total = engagement + recency + cross_source + quality_points
        post["rank"] = round(min(100.0, total), 1)
        post["content_available"] = bool(content)
        post["content_quality"] = quality_rating
        post["excerpt"] = (content or post.get("b", "") or "")[:200]

    ranked.sort(key=lambda p: p.get("rank", 0), reverse=True)
    metrics = {
        "total_posts": len(ranked),
        "llm_quality_used": llm_quality is not None,
        "llm_usage": llm_usage,
    }
    return ranked, metrics


def rank_posts(posts: List[Dict], scraped_content: Dict[str, str]) -> List[Dict]:
    """Backwards-compatible ranking entrypoint."""
    ranked, _ = rank_posts_with_metrics(posts, scraped_content)
    return ranked
