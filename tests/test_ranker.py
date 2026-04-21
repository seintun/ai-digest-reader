from ranker import rank_posts
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
