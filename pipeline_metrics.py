"""Run metrics and cost estimation for content-aware pipeline."""
from __future__ import annotations

from typing import Dict


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
        f"- Session Model Cost (USD): `${cost.get('session_model_usd', 0):.6f}`",
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
