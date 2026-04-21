"""Multi-signal ranking for digest stories."""
from __future__ import annotations

import json
import math
import os
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse


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


def _rate_content_quality(posts: List[Dict], scraped_content: Dict[str, str]) -> Optional[Dict[str, int]]:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return None
    candidates = []
    for post in posts:
        content = scraped_content.get(post.get("u", ""), "") or ""
        excerpt = content[:200].strip()
        if excerpt:
            candidates.append((post.get("i", ""), excerpt))
    if not candidates:
        return None

    lines = [
        "Rate each excerpt for substance from 1 (clickbait/thin) to 10 (highly substantive).",
        "Output only JSON object in this exact format: {\"ratings\": [{\"id\": \"rd-0\", \"rating\": 7}]}",
    ]
    for story_id, excerpt in candidates:
        lines.append(f"[{story_id}] {excerpt}")
    prompt = "\n".join(lines)

    try:
        from openai import OpenAI

        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            default_headers={
                "HTTP-Referer": "https://dailydigest.vercel.app",
                "X-Title": "DailyDigest",
            },
        )
        response = client.chat.completions.create(
            model="moonshotai/kimi-k2",
            messages=[{"role": "user", "content": prompt}],
            timeout=60,
        )
        raw = response.choices[0].message.content or ""
    except Exception:
        return None

    parsed = _parse_json_object(raw)
    if not parsed:
        return None
    items = parsed.get("ratings")
    if not isinstance(items, list):
        return None

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
    return ratings or None


def rank_posts(posts: List[Dict], scraped_content: Dict[str, str]) -> List[Dict]:
    """Score and rank posts with rank/content metadata."""
    ranked = [dict(post) for post in posts]
    cross_source_scores = _compute_cross_source_scores(ranked)
    llm_quality = _rate_content_quality(ranked, scraped_content)

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
    return ranked
