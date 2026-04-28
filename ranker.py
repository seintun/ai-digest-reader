"""Multi-signal ranking for digest stories."""
from __future__ import annotations

import hashlib
import math
import os
import json
import shlex
import subprocess
import re
import time as _time
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeoutError
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

from llm_client import LLMClient
from model_pricing import estimate_llm_cost_usd, usage_to_dict
from schema import extract_excerpt, parse_llm_json

QUALITY_MAX_RETRIES = int(os.environ.get("RANKER_AI_MAX_RETRIES", "0") or "0")
QUALITY_RETRY_SECONDS = (2, 5)
RANKER_AI_CONNECT_TIMEOUT = float(os.environ.get("RANKER_AI_CONNECT_TIMEOUT", "10") or "10")
RANKER_AI_READ_TIMEOUT = float(os.environ.get("RANKER_AI_READ_TIMEOUT", "20") or "20")
RANKER_BATCH_TIMEOUT_SECONDS = float(os.environ.get("RANKER_BATCH_TIMEOUT_SECONDS", "200") or "200")
OPENCLAW_RANKER_TIMEOUT_SECONDS = float(os.environ.get("OPENCLAW_RANKER_TIMEOUT_SECONDS", "120") or "120")
_MIN_EXCERPT_LEN = 80


def _source_from_id(story_id: str) -> str:
    return (story_id or "").split("-", 1)[0]


def _path_signature(url: str) -> Tuple[str, str]:
    parsed = urlparse(url or "")
    domain = (parsed.netloc or "").lower()
    path = re.sub(r"/+", "/", (parsed.path or "/")).rstrip("/") or "/"
    return domain, path


def _compute_cross_source_scores(posts: List[Dict]) -> Dict[str, float]:
    buckets: Dict[str, List[Dict]] = {}
    for post in posts:
        url = post.get("u", "")
        domain, path = _path_signature(url)
        if not domain:
            continue
        key = hashlib.sha256((domain + path).encode()).hexdigest()
        buckets.setdefault(key, []).append(post)

    scores: Dict[str, float] = {}
    for post in posts:
        story_id = post.get("i", "")
        url = post.get("u", "")
        domain, path = _path_signature(url)
        if not domain:
            scores[story_id] = 0.0
            continue
        key = hashlib.sha256((domain + path).encode()).hexdigest()
        bucket = buckets.get(key, [post])
        unique_sources = {_source_from_id(p.get("i", "")) for p in bucket}
        points = min(20.0, 5.0 * max(0, len(unique_sources) - 1))
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
    now = datetime.now(timezone.utc).timestamp()
    ts = post.get("ts")
    try:
        age_hours = max(0.0, (now - float(ts)) / 3600.0) if ts else 24.0
    except (TypeError, ValueError):
        age_hours = 24.0
    freshness_factor = 1.0 / math.sqrt(age_hours + 1.0)
    adjusted_score = score * freshness_factor
    normalized_score = min(adjusted_score / 2000.0, 1.0) * 18.0
    normalized_comments = min(comments / 1000.0, 1.0) * 12.0
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


def _quality_candidates(posts: List[Dict], scraped_content: Dict[str, str]) -> List[Tuple[str, str]]:
    candidates: List[Tuple[str, str]] = []
    for post in posts:
        content = scraped_content.get(post.get("u", ""), "") or ""
        excerpt = extract_excerpt(content, max_chars=150) or extract_excerpt(post.get("b", "") or "", max_chars=150)
        if excerpt and len(excerpt) >= _MIN_EXCERPT_LEN:
            candidates.append((post.get("i", ""), excerpt))
    return candidates


def _quality_prompt(candidates: List[Tuple[str, str]]) -> str:
    lines = [
        "Rate each excerpt for substance from 1 (clickbait/thin) to 10 (highly substantive).",
        'Output only JSON: {"ratings": [{"id": "rd-0", "rating": 7}, ...]}',
    ]
    for story_id, excerpt in candidates:
        lines.append(f'[{story_id}] "{excerpt}"')
    return "\n".join(lines)


def _request_quality_ratings(
    candidates: List[Tuple[str, str]],
    connect_timeout: float,
    read_timeout: float,
    batch_num: int = 0,
) -> Tuple[Optional[Dict[str, int]], Dict]:
    # Each worker creates its own LLMClient (and requests.Session) —
    # requests.Session is not thread-safe under concurrent use.
    client = LLMClient(connect_timeout=connect_timeout, read_timeout=read_timeout)
    if not candidates:
        return None, usage_to_dict(0, 0)
    prompt = _quality_prompt(candidates)
    label = f"[batch {batch_num}] " if batch_num else ""
    print(f"Ranking AI: {label}scoring {len(candidates)} excerpts...", flush=True)
    content, usage = client.complete(prompt)
    if not content:
        print(f"Ranking AI: {label}failed (no content from LLM)")
        return None, usage
    parsed = parse_llm_json(content)
    if not parsed:
        print(f"Ranking AI: {label}failed (JSON parse error)")
        return None, usage
    items = parsed.get("ratings")
    if not isinstance(items, list):
        print(f"Ranking AI: {label}failed (unexpected JSON shape)")
        return None, usage
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
    print(f"Ranking AI: {label}done — {len(ratings)}/{len(candidates)} rated")
    return ratings or None, usage


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
    usd_per_1k_tokens = float(os.environ.get("RANKER_AI_ESTIMATE_USD_PER_1K_TOKENS", "0.01") or "0.01")
    estimated_total_tokens = estimated_input_tokens + estimated_output_tokens
    return round((estimated_total_tokens / 1000.0) * usd_per_1k_tokens, 6)


def _ranker_ai_enabled() -> bool:
    value = (os.environ.get("RANKER_AI_ENABLED") or "1").strip().lower()
    return value not in {"0", "false", "no", "off"}


def _ranker_ai_provider() -> str:
    return (os.environ.get("RANKER_AI_PROVIDER") or os.environ.get("AI_DIGEST_RANKER_PROVIDER") or "direct_openrouter").strip().lower()


def _openclaw_quality_command() -> list[str]:
    raw = (os.environ.get("AI_DIGEST_OPENCLAW_RANKER_COMMAND") or os.environ.get("OPENCLAW_RANKER_COMMAND") or "openclaw ai complete --json").strip()
    return shlex.split(raw)


def _parse_quality_ratings_payload(content: str, valid_ids: set[str]) -> tuple[Optional[Dict[str, int]], Dict[str, int]]:
    try:
        parsed = parse_llm_json(content) or json.loads(content)
    except Exception:
        return None, {"invalid_ignored": 1, "extras_ignored": 0}
    items = parsed.get("ratings") if isinstance(parsed, dict) else parsed
    if not isinstance(items, list):
        return None, {"invalid_ignored": 1, "extras_ignored": 0}
    ratings: Dict[str, int] = {}
    invalid = 0
    extras = 0
    for item in items:
        if not isinstance(item, dict):
            invalid += 1
            continue
        story_id = str(item.get("id") or item.get("story_id") or "")
        if story_id not in valid_ids:
            extras += 1
            continue
        raw_rating = item.get("rating", item.get("quality"))
        try:
            rating_int = int(raw_rating)
        except (TypeError, ValueError):
            invalid += 1
            continue
        if not 1 <= rating_int <= 10:
            invalid += 1
            continue
        ratings[story_id] = rating_int
    return ratings or None, {"invalid_ignored": invalid, "extras_ignored": extras}


def _request_openclaw_quality_ratings(candidates: List[Tuple[str, str]]) -> Tuple[Optional[Dict[str, int]], Dict]:
    if not candidates:
        return None, usage_to_dict(0, 0)
    prompt = _quality_prompt(candidates)
    estimated_input_tokens = max(1, len(prompt) // 4)
    estimated_output_tokens = max(20, 12 * len(candidates))
    # OpenRouter pricing for openai/gpt-5.5 is $5/M input and $30/M output tokens.
    # Override these if OpenClaw routes the ranker through a different paid model.
    input_rate = float(os.environ.get("OPENCLAW_RANKER_INPUT_USD_PER_MILLION_TOKENS", os.environ.get("RANKER_AI_INPUT_USD_PER_MILLION_TOKENS", "5")) or "5")
    output_rate = float(os.environ.get("OPENCLAW_RANKER_OUTPUT_USD_PER_MILLION_TOKENS", os.environ.get("RANKER_AI_OUTPUT_USD_PER_MILLION_TOKENS", "30")) or "30")
    usage = usage_to_dict(0, 0)
    usage.update({
        "input_tokens": estimated_input_tokens,
        "output_tokens": estimated_output_tokens,
        "total_tokens": estimated_input_tokens + estimated_output_tokens,
        "cost_usd": estimate_llm_cost_usd(
            estimated_input_tokens,
            estimated_output_tokens,
            input_usd_per_million_tokens=input_rate,
            output_usd_per_million_tokens=output_rate,
        ),
        "cost_source": "openclaw_static_estimate",
        "cost_label": f"estimated at ${input_rate:g}/M input + ${output_rate:g}/M output tokens; actual OpenClaw marginal cost may be free/subscription/unknown",
        "ranker_ai_provider": "openclaw",
        "requested_model": os.environ.get("OPENCLAW_RANKER_MODEL", "openclaw-current"),
        "estimated_tokens": estimated_input_tokens + estimated_output_tokens,
        "estimated_input_tokens": estimated_input_tokens,
        "estimated_output_tokens": estimated_output_tokens,
        "estimate_input_usd_per_million_tokens": input_rate,
        "estimate_output_usd_per_million_tokens": output_rate,
        "ai_parallel_enabled": False,
        "ai_parallel_workers": 1,
        "ai_batches": 1,
        "ai_parallel_fallback_reason": "",
    })
    print(f"Ranking AI: OpenClaw scoring {len(candidates)} excerpts...", flush=True)
    try:
        completed = subprocess.run(
            _openclaw_quality_command(),
            input=prompt,
            text=True,
            capture_output=True,
            timeout=OPENCLAW_RANKER_TIMEOUT_SECONDS,
            check=False,
        )
    except FileNotFoundError:
        usage["ai_parallel_fallback_reason"] = "openclaw_cli_missing"
        return None, usage
    except subprocess.TimeoutExpired:
        usage["ai_parallel_fallback_reason"] = "openclaw_timeout"
        return None, usage
    except Exception as exc:
        usage["ai_parallel_fallback_reason"] = f"openclaw_error:{type(exc).__name__}"
        return None, usage
    if completed.returncode != 0:
        usage["ai_parallel_fallback_reason"] = "openclaw_nonzero_exit"
        usage["openclaw_stderr"] = completed.stderr.strip()[:500]
        return None, usage
    ratings, parse_metrics = _parse_quality_ratings_payload(completed.stdout, {story_id for story_id, _ in candidates})
    usage.update(parse_metrics)
    if not ratings:
        usage["ai_parallel_fallback_reason"] = "openclaw_parse_failed"
        return None, usage
    usage["rated"] = len(ratings)
    print(f"Ranking AI: OpenClaw done — {len(ratings)}/{len(candidates)} rated")
    return ratings, usage


def _rate_content_quality(posts: List[Dict], scraped_content: Dict[str, str]) -> Tuple[Optional[Dict[str, int]], Dict[str, float | int | str]]:
    if not _ranker_ai_enabled():
        usage = usage_to_dict(0, 0)
        usage.update({
            "ai_parallel_enabled": False,
            "ai_parallel_workers": 0,
            "ai_batches": 0,
            "ai_parallel_fallback_reason": "ranker_ai_disabled",
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

    provider = _ranker_ai_provider()
    if provider == "openclaw":
        return _request_openclaw_quality_ratings(candidates)
    if provider not in {"direct_openrouter", "openrouter"}:
        usage = usage_to_dict(0, 0)
        usage.update({
            "ai_parallel_enabled": False,
            "ai_parallel_workers": 0,
            "ai_batches": 0,
            "ai_parallel_fallback_reason": f"unsupported_provider:{provider}",
            "ranker_ai_provider": provider,
        })
        return None, usage

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        usage = usage_to_dict(0, 0)
        usage.update({
            "ai_parallel_enabled": False,
            "ai_parallel_workers": 0,
            "ai_batches": 0,
            "ai_parallel_fallback_reason": "missing_api_key",
            "ranker_ai_provider": provider,
        })
        return None, usage

    configured_workers = int(os.environ.get("RANKER_AI_PARALLEL_WORKERS", "8") or "8")
    configured_workers = max(1, min(configured_workers, 16))
    max_usd = float(os.environ.get("RANKER_AI_PARALLEL_MAX_USD", "0.12") or "0.12")
    projected_usd = _estimate_quality_cost_usd(candidates, configured_workers)

    fallback_reason = ""
    workers = configured_workers
    if workers > 1 and projected_usd > max_usd:
        workers = 1
        fallback_reason = "projected_cost_exceeded"

    batches = _chunk_candidates(candidates, workers)
    avg_batch = math.ceil(len(candidates) / max(1, len(batches)))
    print(f"Ranking AI: {len(candidates)} candidates → {len(batches)} batch(es) ×~{avg_batch} each, workers={workers}")
    ratings: Dict[str, int] = {}
    input_tokens = 0
    output_tokens = 0
    summed_cost_usd = 0.0
    saw_provider_cost = False
    saw_estimated_cost = False
    batch_count = len(batches)

    def _accumulate(batch_ratings, usage):
        nonlocal input_tokens, output_tokens, summed_cost_usd, saw_provider_cost, saw_estimated_cost
        input_tokens += int(usage.get("input_tokens", 0) or 0)
        output_tokens += int(usage.get("output_tokens", 0) or 0)
        summed_cost_usd += float(usage.get("cost_usd", 0.0) or 0.0)
        if usage.get("cost_source") == "openrouter_usage" and usage.get("openrouter_reported_cost_credits") is not None:
            saw_provider_cost = True
        else:
            saw_estimated_cost = True
        if batch_ratings:
            ratings.update(batch_ratings)

    batch_start = _time.monotonic()
    done_count = 0

    def _request_quality_ratings_compat(batch, batch_num: int):
        try:
            return _request_quality_ratings(
                batch, RANKER_AI_CONNECT_TIMEOUT, RANKER_AI_READ_TIMEOUT, batch_num=batch_num
            )
        except TypeError as exc:
            # Older tests and callers may monkeypatch _request_quality_ratings with
            # the pre-progress-label signature. Keep that seam compatible.
            if "batch_num" not in str(exc):
                raise
            return _request_quality_ratings(batch, RANKER_AI_CONNECT_TIMEOUT, RANKER_AI_READ_TIMEOUT)

    if workers == 1:
        batch_ratings, usage = _request_quality_ratings_compat(batches[0], 1)
        done_count += 1
        elapsed = round(_time.monotonic() - batch_start, 1)
        print(f"Ranking AI: [1/{batch_count}] returned ({elapsed}s)", flush=True)
        _accumulate(batch_ratings, usage)
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = [
                pool.submit(_request_quality_ratings_compat, batch, i + 1)
                for i, batch in enumerate(batches)
            ]
            try:
                for future in as_completed(futures, timeout=RANKER_BATCH_TIMEOUT_SECONDS):
                    batch_ratings, usage = future.result()
                    done_count += 1
                    elapsed = round(_time.monotonic() - batch_start, 1)
                    print(f"Ranking AI: [{done_count}/{batch_count}] returned ({elapsed}s)", flush=True)
                    _accumulate(batch_ratings, usage)
            except FuturesTimeoutError:
                remaining = batch_count - done_count
                elapsed = round(_time.monotonic() - batch_start, 1)
                print(
                    f"Ranking AI: timed out after {elapsed}s — "
                    f"{remaining}/{batch_count} batch(es) dropped, heuristics used for those",
                    flush=True,
                )

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
        "ranker_ai_provider": provider,
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
            quality_points = (quality_rating / 10.0) * 35.0

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
