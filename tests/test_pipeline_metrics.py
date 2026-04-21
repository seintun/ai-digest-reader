from pipeline_metrics import (
    count_ranking_chars,
    count_summary_chars,
    estimate_llm_cost_usd,
    render_dashboard,
)


def test_count_ranking_chars_caps_each_excerpt():
    excerpts = ["a" * 50, "b" * 500]
    assert count_ranking_chars(excerpts) == 250


def test_count_summary_chars_caps_each_content():
    contents = ["x" * 100, "y" * 3000]
    assert count_summary_chars(contents) == 2100


def test_estimate_llm_cost_usd_is_positive_and_rounded():
    cost = estimate_llm_cost_usd(ranking_chars=8000, summary_chars=30000)
    assert cost == 0.17


def test_render_dashboard_includes_key_sections():
    markdown = render_dashboard(
        {
            "runtime": {"total_seconds": 12.3, "within_budget": True},
            "cost": {"estimated_usd": 0.12, "within_budget": True},
            "scraping": {"candidate_urls": 10, "success_rate": 80.0, "cache_hit_rate": 40.0},
            "ranking": {"total_posts": 20, "llm_quality_used": True},
            "summary": {"source": "openrouter", "generated": True},
            "degradation": {
                "scraping_fallback_used": False,
                "ranking_fallback_used": False,
                "summary_fallback_used": False,
                "no_summary_fallback_used": False,
            },
        }
    )
    assert "Content-Aware Pipeline Monitoring" in markdown
    assert "## Scraping" in markdown
    assert "## Degradation Path" in markdown
