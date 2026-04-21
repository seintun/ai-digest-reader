from pipeline_metrics import render_dashboard


def test_render_dashboard_includes_key_sections():
    markdown = render_dashboard(
        {
            "runtime": {"total_seconds": 12.3, "within_budget": True},
            "cost": {"session_model_usd": 0.12, "within_budget": True},
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
