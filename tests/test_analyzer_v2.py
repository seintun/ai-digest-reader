from unittest.mock import MagicMock, patch

import analyzer_v2
from analyzer_v2 import _build_prompt


def _make_post(**kwargs):
    base = {
        "i": "rd-0",
        "t": "Top Story",
        "u": "https://example.com/story",
        "rank": 95.2,
        "s": 123,
        "c": 45,
        "content_quality": 8,
        "content": "This is a substantive article about technology.",
    }
    base.update(kwargs)
    return base


def test_build_prompt_contains_ranked_story_fields():
    ranked_posts = [_make_post()]
    prompt = _build_prompt(ranked_posts)
    assert "Top Stories (Ranked by Importance)" in prompt
    assert "[rd-0] [95.2/100] Top Story" in prompt
    assert "quality:8/10" in prompt


def test_build_prompt_uses_compact_excerpt():
    long_content = "This is a very long article. " * 100
    ranked_posts = [_make_post(content=long_content)]
    prompt = _build_prompt(ranked_posts)
    # excerpt should be capped at 200 chars, not full content
    assert len(long_content) > 200
    assert long_content not in prompt


def test_build_prompt_includes_source_label():
    ranked_posts = [_make_post(i="hn-0", sn="")]
    prompt = _build_prompt(ranked_posts)
    assert "src:HN" in prompt


def test_build_prompt_includes_url():
    ranked_posts = [_make_post()]
    prompt = _build_prompt(ranked_posts)
    assert "https://example.com/story" in prompt


def test_generate_summary_with_meta_returns_none_when_client_fails(monkeypatch):
    mock_client = MagicMock()
    mock_client.complete.return_value = (None, {"input_tokens": 0, "output_tokens": 0})

    with patch("analyzer_v2.LLMClient", return_value=mock_client):
        summary, meta = analyzer_v2.generate_summary_with_meta([_make_post()])

    assert summary is None
    assert meta["generated"] is False


def test_generate_summary_with_meta_returns_none_for_empty_posts():
    summary, meta = analyzer_v2.generate_summary_with_meta([])
    assert summary is None
    assert meta["source"] == "none"


def test_generate_summary_returns_none_on_invalid_json(monkeypatch):
    mock_client = MagicMock()
    mock_client.complete.return_value = ("not valid json", {"input_tokens": 10, "output_tokens": 5})

    with patch("analyzer_v2.LLMClient", return_value=mock_client):
        summary, meta = analyzer_v2.generate_summary_with_meta([_make_post()])

    assert summary is None
    assert meta["generated"] is False


def test_build_prompt_labels_verified_content_stories():
    """Stories with scraped content are labeled so the LLM knows the evidence is real."""
    prompt = _build_prompt([_make_post(content="Substantive article body text here.")])
    assert "evidence:verified-content" in prompt


def test_build_prompt_labels_title_only_stories():
    """Stories with no scraped content are flagged title-only so the LLM doesn't invent details."""
    prompt = _build_prompt([_make_post(content="", excerpt="", b="")])
    assert "evidence:title-only" in prompt


def test_build_prompt_respects_excerpt_chars():
    long_content = "Sentence about technology. " * 40
    prompt = _build_prompt([_make_post(content=long_content)], excerpt_chars=400)
    # The excerpt line should be present and bounded near the requested length.
    excerpt_line = [line for line in prompt.splitlines() if line.startswith("excerpt:")]
    assert excerpt_line
    assert len(excerpt_line[0]) <= len('excerpt: ""') + 400 + 1
