import json
import sys

from engine.config import DigestEngineConfig
from engine.openclaw import generate_summary_with_openclaw, validate_grounded_summary


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


def test_validate_grounded_summary_rejects_missing_story_id():
    summary = _summary()
    summary["structured"]["mustRead"][0]["id"] = "fake"
    valid, warnings = validate_grounded_summary(summary, _posts())
    assert not valid
    assert "fake" in warnings[0]


def test_generate_summary_with_openclaw_reads_payload_from_command(tmp_path):
    payload = {"summary": _summary(), "metrics": {"engine": {"name": "openclaw"}}}
    script = tmp_path / "fake_openclaw.py"
    script.write_text(
        "import json, sys\n"
        "out=sys.argv[sys.argv.index('--output')+1]\n"
        f"json.dump({payload!r}, open(out, 'w'))\n"
    )
    config = DigestEngineConfig(engine="openclaw", openclaw_stages=("summary",), openclaw_command=f"{sys.executable} {script}")
    summary, meta = generate_summary_with_openclaw(_posts(), config)
    assert summary["schema_version"] == "2"
    assert meta["generated"] is True
    assert meta["source"] == "openclaw"
