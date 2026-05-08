import json
from unittest.mock import patch

from engine.config import DigestEngineConfig
from engine.summary import generate_summary_with_provider


def _posts():
    return [
        {"i": "rd-0", "t": "A", "u": "https://example.com/a", "rank": 90},
        {"i": "hn-0", "t": "B", "u": "https://example.com/b", "rank": 80},
        {"i": "rs-0", "t": "C", "u": "https://example.com/c", "rank": 70},
    ]


def _summary():
    return {
        "schema_version": "2",
        "simple": "A short summary.",
        "structured": {
            "themes": ["AI", "Tools", "Policy"],
            "breaking": "A",
            "mustRead": [
                {"id": "rd-0", "title": "A", "url": "https://example.com/a", "reason": "Important."},
                {"id": "hn-0", "title": "B", "url": "https://example.com/b", "reason": "Important."},
                {"id": "rs-0", "title": "C", "url": "https://example.com/c", "reason": "Important."},
            ],
        },
        "fullBrief": {
            "intro": "Intro.",
            "sections": [{"heading": "A", "body": "Body."}, {"heading": "B", "body": "Body."}],
            "closing": "Close.",
        },
    }


def test_hermes_provider_uses_cli_and_validates_output():
    config = DigestEngineConfig(summary_provider="hermes", hermes_command="hermes", hermes_provider="omniroute", hermes_model="codex-combo")
    with patch("engine.summary.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = json.dumps(_summary())
        mock_run.return_value.stderr = ""
        summary, meta = generate_summary_with_provider(_posts(), config)
    assert summary is not None
    assert summary["schema_version"] == "2"
    assert meta["source"] == "hermes"
    assert meta["generated"] is True


def test_benchmark_mode_records_both_paths():
    config = DigestEngineConfig(summary_provider="benchmark", summary_primary="hermes", hermes_command="hermes", hermes_provider="omniroute", hermes_model="codex-combo")
    with patch("engine.summary.generate_summary_with_openclaw") as mock_openclaw, patch("engine.summary.generate_summary_with_hermes") as mock_hermes:
        mock_openclaw.return_value = (_summary(), {"source": "openclaw", "generated": True})
        mock_hermes.return_value = (_summary(), {"source": "hermes", "generated": True})
        summary, meta = generate_summary_with_provider(_posts(), config)
    assert summary is not None
    assert meta["generated"] is True
    assert meta["source"] == "hermes"
    assert meta["benchmark"]["openclaw"]["generated"] is True
    assert meta["benchmark"]["hermes"]["generated"] is True
