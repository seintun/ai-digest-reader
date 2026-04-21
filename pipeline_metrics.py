"""Run metrics and cost estimation for content-aware pipeline."""
from __future__ import annotations

from typing import Dict, List

RANKING_COST_PER_CHAR = 0.05 / (40 * 200)
SUMMARY_COST_PER_CHAR = 0.12 / (15 * 2000)


def estimate_llm_cost_usd(ranking_chars: int, summary_chars: int) -> float:
    """Estimate LLM run cost in USD using spec baseline rates."""
    ranking_cost = max(0, ranking_chars) * RANKING_COST_PER_CHAR
    summary_cost = max(0, summary_chars) * SUMMARY_COST_PER_CHAR
    return round(ranking_cost + summary_cost, 4)


def count_ranking_chars(excerpts: List[str]) -> int:
    """Count bounded ranking input chars (200 chars per story)."""
    return sum(len((excerpt or "")[:200]) for excerpt in excerpts)


def count_summary_chars(contents: List[str]) -> int:
    """Count bounded summary input chars (2000 chars per story)."""
    return sum(len((content or "")[:2000]) for content in contents)


def render_dashboard(metrics: Dict) -> str:
    """Render a compact markdown monitoring dashboard."""
    scraping = metrics.get("scraping", {})
    ranking = metrics.get("ranking", {})
    summary = metrics.get("summary", {})
    degradation = metrics.get("degradation", {})
    runtime = metrics.get("runtime", {})
    cost = metrics.get("cost", {})

    lines = [
        "# Content-Aware Pipeline Monitoring",
        "",
        f"- Runtime (s): `{runtime.get('total_seconds', 0):.2f}`",
        f"- Estimated LLM Cost (USD): `${cost.get('estimated_usd', 0):.4f}`",
        f"- Cost Budget Pass (<$0.25): `{cost.get('within_budget', False)}`",
        f"- Runtime Budget Pass (<180s): `{runtime.get('within_budget', False)}`",
        "",
        "## Scraping",
        f"- Candidate URLs: `{scraping.get('candidate_urls', 0)}`",
        f"- Success Rate: `{scraping.get('success_rate', 0):.1f}%`",
        f"- Cache Hit Rate: `{scraping.get('cache_hit_rate', 0):.1f}%`",
        "",
        "## Ranking",
        f"- Ranked Posts: `{ranking.get('total_posts', 0)}`",
        f"- LLM Quality Used: `{ranking.get('llm_quality_used', False)}`",
        "",
        "## Summary",
        f"- Source: `{summary.get('source', 'none')}`",
        f"- Generated: `{summary.get('generated', False)}`",
        "",
        "## Degradation Path",
        f"- Scraping fallback used: `{degradation.get('scraping_fallback_used', False)}`",
        f"- Ranking fallback used: `{degradation.get('ranking_fallback_used', False)}`",
        f"- Summary v1 fallback used: `{degradation.get('summary_fallback_used', False)}`",
        f"- No-summary fallback used: `{degradation.get('no_summary_fallback_used', False)}`",
        "",
    ]
    return "\n".join(lines)
