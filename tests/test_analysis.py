from unittest.mock import MagicMock

import engine.analysis as analysis
from engine.config import DigestEngineConfig


def _valid_analysis():
    return {
        "implications": ["Engineers should X", "Industry should Y"],
        "skeptic_take": "This could be overhyped because Z",
        "confidence": "medium",
        "evidence_basis": ["3 stories verified via primary sources", "2 stories title-only"],
    }


def test_validate_analysis_accepts_well_formed():
    assert analysis.validate_analysis(_valid_analysis()) is True


def test_validate_analysis_rejects_missing_keys():
    bad = _valid_analysis()
    del bad["skeptic_take"]
    assert analysis.validate_analysis(bad) is False


def test_validate_analysis_rejects_bad_confidence():
    bad = _valid_analysis()
    bad["confidence"] = "maybe"
    assert analysis.validate_analysis(bad) is False


def test_validate_analysis_rejects_non_dict():
    assert analysis.validate_analysis("nope") is False
    assert analysis.validate_analysis(None) is False


def test_validate_analysis_requires_nonempty_implications():
    bad = _valid_analysis()
    bad["implications"] = []
    assert analysis.validate_analysis(bad) is False


def test_build_analysis_prompt_includes_summary_signal():
    summary = {
        "simple": "TLDR text",
        "structured": {"themes": ["agents", "pricing", "safety"], "breaking": "Big launch", "mustRead": []},
    }
    posts = [{"i": "hn-0", "t": "DeepSeek V4 Flash released", "content_available": True}]
    prompt = analysis._build_analysis_prompt(summary, posts)
    assert "Big launch" in prompt
    assert "agents" in prompt
    assert "DeepSeek V4 Flash released" in prompt
    assert "content_available" in prompt or "verified" in prompt.lower()


def test_generate_analysis_returns_none_when_hermes_fails(monkeypatch):
    config = DigestEngineConfig()
    monkeypatch.setattr(analysis, "_hermes_analysis_command", lambda cfg, prompt: (None, {"cost_source": "hermes_cli_error"}))
    summary = {"simple": "x", "structured": {"themes": ["a", "b", "c"], "breaking": "y", "mustRead": []}}
    result, meta = analysis.generate_analysis_with_hermes(summary, [{"i": "hn-0", "t": "t"}], config)
    assert result is None
    assert meta["generated"] is False


def test_generate_analysis_parses_valid_json(monkeypatch):
    config = DigestEngineConfig()
    import json
    payload = json.dumps(_valid_analysis())
    monkeypatch.setattr(analysis, "_hermes_analysis_command", lambda cfg, prompt: (payload, {"cost_source": "hermes_cli"}))
    summary = {"simple": "x", "structured": {"themes": ["a", "b", "c"], "breaking": "y", "mustRead": []}}
    result, meta = analysis.generate_analysis_with_hermes(summary, [{"i": "hn-0", "t": "t"}], config)
    assert result is not None
    assert result["confidence"] == "medium"
    assert meta["generated"] is True


def test_generate_analysis_rejects_invalid_json(monkeypatch):
    config = DigestEngineConfig()
    monkeypatch.setattr(analysis, "_hermes_analysis_command", lambda cfg, prompt: ("not json at all", {"cost_source": "hermes_cli"}))
    summary = {"simple": "x", "structured": {"themes": ["a", "b", "c"], "breaking": "y", "mustRead": []}}
    result, meta = analysis.generate_analysis_with_hermes(summary, [{"i": "hn-0", "t": "t"}], config)
    assert result is None
    assert meta["generated"] is False


def test_generate_analysis_tolerates_cli_reasoning_preamble(monkeypatch):
    """The Hermes CLI emits a warning line + reasoning box before the JSON; parsing must skip it."""
    config = DigestEngineConfig()
    import json
    payload = (
        "Warning: Unknown toolsets: messaging\n\n"
        "┌─ Reasoning ──────────────────────────────┐\n"
        "The user wants me to analyze...\n"
        "└──────────────────────────────────────────┘\n\n"
        + json.dumps(_valid_analysis())
    )
    monkeypatch.setattr(analysis, "_hermes_analysis_command", lambda cfg, prompt: (payload, {"cost_source": "hermes_cli"}))
    summary = {"simple": "x", "structured": {"themes": ["a", "b", "c"], "breaking": "y", "mustRead": []}}
    result, meta = analysis.generate_analysis_with_hermes(summary, [{"i": "hn-0", "t": "t"}], config)
    assert result is not None
    assert result["skeptic_take"].startswith("This could be overhyped")
    assert meta["generated"] is True
