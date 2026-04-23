from ranker import rank_posts, rank_posts_with_metrics
import ranker


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


def test_ranker_falls_back_when_llm_quality_unavailable(monkeypatch):
    monkeypatch.setattr(ranker, "_rate_content_quality", lambda _posts, _content: (None, {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0}))
    posts = [{"i": "rd-0", "u": "https://example.com/a", "s": 100, "c": 20, "b": "body"}]
    ranked = rank_posts(posts, {})
    assert ranked[0]["content_quality"] == 0


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
