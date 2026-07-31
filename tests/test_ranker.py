from ranker import rank_posts, rank_posts_with_metrics
import ranker


def test_title_quality_heuristic_boosts_substantive_titles():
    substantive = {"t": "OpenAI releases GPT-5.6 with native filesystem MCP support"}
    clickbait = {"t": "Day 32 of building GTA 6 using claude"}
    high = ranker._title_quality_heuristic(substantive)
    low = ranker._title_quality_heuristic(clickbait)
    assert high > low
    assert 0.0 <= high <= 10.0
    assert 0.0 <= low <= 10.0


def test_title_quality_heuristic_penalizes_meta_posts():
    meta = {"t": "r/ClaudeAI List of Ongoing Megathreads"}
    assert ranker._title_quality_heuristic(meta) < 5.0


def test_unscraped_posts_get_title_heuristic_quality_when_llm_off(monkeypatch):
    """When the LLM ranker is disabled, unscraped posts must not all tie at quality 0."""
    monkeypatch.setenv("RANKER_AI_ENABLED", "0")
    posts = [
        {"i": "rd-0", "u": "https://example.com/a", "s": 10, "c": 2,
         "t": "Anthropic launches Claude Sonnet 5 with near-Opus performance"},
        {"i": "rd-1", "u": "https://example.com/b", "s": 10, "c": 2,
         "t": "Scrolling through r/ClaudeAI"},
    ]
    ranked, metrics = rank_posts_with_metrics(posts, {})  # no scraped content
    assert metrics["llm_quality_used"] is False
    by_id = {p["i"]: p for p in ranked}
    # Substantive title scores higher than the meta/vague title — no dead tie.
    assert by_id["rd-0"]["content_quality"] > by_id["rd-1"]["content_quality"]
    assert by_id["rd-0"]["content_quality"] > 0


def test_scraped_post_still_uses_llm_or_excerpt_heuristic_not_title(monkeypatch):
    """When content IS available, the title heuristic must not override content-based quality."""
    monkeypatch.setenv("RANKER_AI_ENABLED", "0")
    posts = [{"i": "rd-0", "u": "https://example.com/a", "s": 10, "c": 2,
              "t": "Day 32 of building GTA 6 using claude"}]  # low-quality title
    scraped = {"https://example.com/a": "Substantive article body text. " * 20}
    ranked, _ = rank_posts_with_metrics(posts, scraped)
    # Long scraped excerpt -> _heuristic_quality returns 7, not the low title score.
    assert ranked[0]["content_quality"] == 7


def test_rank_posts_adds_expected_fields():
    posts = [
        {"i": "rd-0", "u": "https://example.com/a", "s": 500, "c": 100, "b": "Short body", "ts": 1_700_000_000},
        {"i": "hn-0", "u": "https://example.com/b", "s": 100, "c": 10, "b": "Another body", "ts": 1_700_000_100},
    ]
    ranked = rank_posts(posts, {"https://example.com/a": "Long article text " * 30})
    assert len(ranked) == 2
    for post in ranked:
        assert "rank" in post
        assert "content_available" in post
        assert "content_quality" in post
        assert "excerpt" in post


def test_rank_posts_sorts_descending_by_rank():
    posts = [
        {"i": "rd-0", "u": "https://example.com/a", "s": 1000, "c": 200, "ts": 1_800_000_000},
        {"i": "hn-0", "u": "https://example.com/b", "s": 5, "c": 0, "ts": 1_100_000_000},
    ]
    ranked = rank_posts(posts, {})
    assert ranked[0]["i"] == "rd-0"


def test_cross_source_signal_applies_to_same_story_across_sources():
    posts = [
        {"i": "rd-0", "u": "https://example.com/story/launch-v2", "s": 20, "c": 5},
        {"i": "hn-0", "u": "https://example.com/story/launch-v2?utm=hn", "s": 15, "c": 4},
        {"i": "rs-0", "u": "https://other.com/unrelated", "s": 0, "c": 0},
    ]
    ranked = rank_posts(posts, {})
    by_id = {p["i"]: p for p in ranked}
    assert by_id["rd-0"]["rank"] > by_id["rs-0"]["rank"]
    assert by_id["hn-0"]["rank"] > by_id["rs-0"]["rank"]


def test_cross_source_signal_counts_rss_as_distinct_source():
    """A story appearing on HN AND RSS gets the cross-source boost (RSS is a real source)."""
    posts = [
        {"i": "hn-0", "u": "https://example.com/story/deepseek-v4", "s": 10, "c": 2},
        {"i": "rs-0", "u": "https://example.com/story/deepseek-v4", "s": 10, "c": 2},
        {"i": "hn-1", "u": "https://example.com/solo-story", "s": 10, "c": 2},
    ]
    scores = ranker._compute_cross_source_scores(posts)
    # hn-0 and rs-0 share a canonical URL across two distinct sources -> boost.
    assert scores["hn-0"] > 0
    assert scores["rs-0"] > 0
    assert scores["hn-0"] == scores["rs-0"]
    # hn-1 appears once -> no cross-source boost.
    assert scores["hn-1"] == 0.0


def test_ranker_falls_back_when_llm_quality_unavailable(monkeypatch):
    monkeypatch.setattr(ranker, "_rate_content_quality", lambda _posts, _content: (None, {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}))
    posts = [{"i": "rd-0", "u": "https://example.com/a", "s": 100, "c": 20, "b": "body"}]
    ranked = rank_posts(posts, {})
    # No scraped content and no LLM -> title heuristic (neutral baseline, not a flat 0).
    assert ranked[0]["content_quality"] > 0


def test_ranker_parallel_batches_merge_metrics(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("RANKER_AI_PARALLEL_WORKERS", "3")
    monkeypatch.setenv("RANKER_AI_PARALLEL_MAX_USD", "1.0")

    calls = []

    def fake_request(candidates, connect_timeout, read_timeout):
        calls.append([story_id for story_id, _ in candidates])
        ratings = {story_id: 8 for story_id, _ in candidates}
        usage = {"input_tokens": 10, "output_tokens": 5, "cost_usd": 0.0001}
        return ratings, usage

    monkeypatch.setattr(ranker, "_request_quality_ratings", fake_request)
    posts = [
        {"i": f"rd-{idx}", "u": f"https://example.com/{idx}", "s": 10, "c": 2, "b": "body"}
        for idx in range(7)
    ]
    scraped = {f"https://example.com/{idx}": "article text " * 20 for idx in range(7)}
    ranked, metrics = rank_posts_with_metrics(posts, scraped)
    assert len(calls) >= 2
    assert metrics["llm_quality_used"] is True
    assert metrics["llm_usage"]["ai_parallel_enabled"] is True
    assert metrics["llm_usage"]["ai_parallel_workers"] == 3
    assert metrics["llm_usage"]["ai_batches"] == len(calls)
    assert all(post["content_quality"] == 8 for post in ranked)


def test_ranker_parallel_falls_back_to_single_worker_on_budget(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("RANKER_AI_PARALLEL_WORKERS", "4")
    monkeypatch.setenv("RANKER_AI_PARALLEL_MAX_USD", "0.0000001")

    calls = []

    def fake_request(candidates, connect_timeout, read_timeout):
        calls.append(len(candidates))
        ratings = {story_id: 6 for story_id, _ in candidates}
        usage = {"input_tokens": 10, "output_tokens": 5, "cost_usd": 0.0001}
        return ratings, usage

    monkeypatch.setattr(ranker, "_request_quality_ratings", fake_request)
    posts = [
        {"i": f"hn-{idx}", "u": f"https://example.com/x{idx}", "s": 10, "c": 1, "b": "body"}
        for idx in range(8)
    ]
    scraped = {f"https://example.com/x{idx}": "text " * 40 for idx in range(8)}
    _, metrics = rank_posts_with_metrics(posts, scraped)
    assert len(calls) == 1
    assert calls[0] == 8
    assert metrics["llm_usage"]["ai_parallel_enabled"] is False
    assert metrics["llm_usage"]["ai_parallel_workers"] == 1
    assert metrics["llm_usage"]["ai_parallel_fallback_reason"] == "projected_cost_exceeded"


def test_ranker_ai_can_be_disabled_even_with_openrouter_key(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("RANKER_AI_ENABLED", "0")

    def fail_request(*_args, **_kwargs):
        raise AssertionError("ranker should not call LLM when RANKER_AI_ENABLED=0")

    monkeypatch.setattr(ranker, "_request_quality_ratings", fail_request)
    posts = [{"i": "rd-0", "u": "https://example.com/a", "s": 100, "c": 20, "b": "body"}]
    scraped = {"https://example.com/a": "article text " * 20}
    _, metrics = rank_posts_with_metrics(posts, scraped)
    assert metrics["llm_quality_used"] is False
    assert metrics["llm_usage"]["ai_parallel_fallback_reason"] == "ranker_ai_disabled"


def test_openclaw_ranker_provider_parses_valid_json(monkeypatch):
    monkeypatch.setenv("RANKER_AI_ENABLED", "1")
    monkeypatch.setenv("AI_DIGEST_RANKER_PROVIDER", "openclaw")

    class Completed:
        returncode = 0
        stdout = '{"ratings":[{"story_id":"rd-0","quality":9},{"story_id":"hn-0","quality":4},{"story_id":"extra","quality":10},{"story_id":"rd-1","quality":99}]}'
        stderr = ""

    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return Completed()

    monkeypatch.setattr(ranker.subprocess, "run", fake_run)
    posts = [
        {"i": "rd-0", "u": "https://example.com/a", "s": 10, "c": 2, "b": "body"},
        {"i": "hn-0", "u": "https://example.com/b", "s": 10, "c": 2, "b": "body"},
    ]
    scraped = {"https://example.com/a": "article text " * 20, "https://example.com/b": "article text " * 20}
    ranked, metrics = rank_posts_with_metrics(posts, scraped)
    by_id = {post["i"]: post for post in ranked}
    assert calls
    assert by_id["rd-0"]["content_quality"] == 9
    assert by_id["hn-0"]["content_quality"] == 4
    assert metrics["llm_quality_used"] is True
    assert metrics["llm_usage"]["ranker_ai_provider"] == "openclaw"
    assert metrics["llm_usage"]["extras_ignored"] == 2
    assert metrics["llm_usage"]["invalid_ignored"] == 0


def test_openclaw_ranker_provider_falls_back_on_failure(monkeypatch):
    monkeypatch.setenv("RANKER_AI_ENABLED", "1")
    monkeypatch.setenv("AI_DIGEST_RANKER_PROVIDER", "openclaw")

    class Completed:
        returncode = 7
        stdout = ""
        stderr = "boom"

    monkeypatch.setattr(ranker.subprocess, "run", lambda *args, **kwargs: Completed())
    posts = [{"i": "rd-0", "u": "https://example.com/a", "s": 10, "c": 2, "b": "body"}]
    scraped = {"https://example.com/a": "article text " * 20}
    ranked, metrics = rank_posts_with_metrics(posts, scraped)
    # OpenClaw failed but scraped content exists -> excerpt-length heuristic (7), not a flat 0.
    assert ranked[0]["content_quality"] == 7
    assert metrics["llm_quality_used"] is False
    assert metrics["llm_usage"]["ai_parallel_fallback_reason"] == "openclaw_nonzero_exit"


def test_ranker_unsupported_provider_falls_back(monkeypatch):
    monkeypatch.setenv("RANKER_AI_ENABLED", "1")
    monkeypatch.setenv("AI_DIGEST_RANKER_PROVIDER", "mystery")
    posts = [{"i": "rd-0", "u": "https://example.com/a", "s": 10, "c": 2, "b": "body"}]
    scraped = {"https://example.com/a": "article text " * 20}
    _, metrics = rank_posts_with_metrics(posts, scraped)
    assert metrics["llm_quality_used"] is False
    assert metrics["llm_usage"]["ai_parallel_fallback_reason"] == "unsupported_provider:mystery"


def test_openclaw_ranker_provider_reports_token_and_cost_estimates(monkeypatch):
    monkeypatch.setenv("RANKER_AI_ENABLED", "1")
    monkeypatch.setenv("AI_DIGEST_RANKER_PROVIDER", "openclaw")
    monkeypatch.setenv("OPENCLAW_RANKER_INPUT_USD_PER_MILLION_TOKENS", "5")
    monkeypatch.setenv("OPENCLAW_RANKER_OUTPUT_USD_PER_MILLION_TOKENS", "30")

    class Completed:
        returncode = 0
        stdout = '{"ratings":[{"story_id":"rd-0","quality":8}]}'
        stderr = ""

    monkeypatch.setattr(ranker.subprocess, "run", lambda *args, **kwargs: Completed())
    posts = [{"i": "rd-0", "u": "https://example.com/a", "s": 10, "c": 2, "b": "body"}]
    scraped = {"https://example.com/a": "article text " * 20}
    _, metrics = rank_posts_with_metrics(posts, scraped)
    usage = metrics["llm_usage"]
    assert usage["cost_source"] == "openclaw_static_estimate"
    assert usage["input_tokens"] > 0
    assert usage["output_tokens"] > 0
    assert usage["total_tokens"] == usage["input_tokens"] + usage["output_tokens"]
    assert usage["cost_usd"] > 0
    assert usage["estimate_input_usd_per_million_tokens"] == 5
    assert usage["estimate_output_usd_per_million_tokens"] == 30
