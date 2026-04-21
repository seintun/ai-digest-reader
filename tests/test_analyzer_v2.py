import analyzer_v2
from analyzer_v2 import _build_prompt


def test_build_prompt_contains_ranked_story_fields():
    ranked_posts = [
        {
            "i": "rd-0",
            "t": "Top Story",
            "rank": 95.2,
            "s": 123,
            "c": 45,
            "content_quality": 8,
            "content": "Deep article text " * 50,
        }
    ]
    prompt = _build_prompt(ranked_posts)
    assert "Top Stories (Ranked by Importance)" in prompt
    assert "[rd-0] [95.2/100] Top Story" in prompt
    assert "Quality: 8/10" in prompt


def test_build_prompt_truncates_content_to_2000_chars():
    ranked_posts = [
        {
            "i": "hn-0",
            "t": "HN Story",
            "rank": 88.7,
            "s": 100,
            "c": 20,
            "content_quality": 7,
            "content": "x" * 2600,
        }
    ]
    prompt = _build_prompt(ranked_posts)
    assert "x" * 2000 in prompt
    assert "x" * 2100 not in prompt


def test_generate_summary_with_meta_returns_none_when_calls_fail(monkeypatch):
    monkeypatch.setattr(analyzer_v2, "_call_openrouter_with_usage", lambda _prompt: (None, {"input_tokens": 0, "output_tokens": 0}))
    monkeypatch.setattr(analyzer_v2, "_call_claude_cli", lambda _prompt: None)
    summary, meta = analyzer_v2.generate_summary_with_meta(
        [{"i": "rd-0", "t": "Story", "rank": 90, "s": 1, "c": 1, "content_quality": 1, "content": "x"}]
    )
    assert summary is None
    assert meta["generated"] is False
