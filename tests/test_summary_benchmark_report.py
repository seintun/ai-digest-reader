import json
from pathlib import Path

from scripts.write_summary_benchmark_report import build_report


def _digest(openclaw_simple="OpenClaw simple", hermes_simple="Hermes simple"):
    return {
        "d": "2026-05-07",
        "g": "2026-05-07T22:21:42.460540",
        "summary": {"simple": "Selected simple"},
        "metrics": {
            "summary": {
                "source": "hermes",
                "benchmark": {
                    "primary": "hermes",
                    "openclaw": {
                        "generated": True,
                        "duration_seconds": 1.234,
                        "summary": {
                            "simple": openclaw_simple,
                            "structured": {"mustRead": [{"id": "a"}, {"id": "b"}]},
                        },
                    },
                    "hermes": {
                        "generated": True,
                        "duration_seconds": 2.345,
                        "summary": {
                            "simple": hermes_simple,
                            "structured": {"mustRead": [{"id": "b"}, {"id": "c"}]},
                        },
                    },
                },
            }
        },
    }


def test_build_report_includes_benchmark_comparison(tmp_path):
    digest_path = tmp_path / "digest.json"
    digest_path.write_text(json.dumps(_digest()), encoding="utf-8")
    report = build_report(_digest(), digest_path)
    assert "AI Digest Summary Report" in report
    assert "OpenClaw: generated (1.234s)" in report
    assert "Hermes: generated (2.345s)" in report
    assert "Overlap: 1 / union 3" in report
    assert "Selected simple" in report


def test_build_report_flags_simple_text_diff(tmp_path):
    digest_path = tmp_path / "digest.json"
    digest = _digest(openclaw_simple="alpha", hermes_simple="beta")
    digest_path.write_text(json.dumps(digest), encoding="utf-8")
    report = build_report(digest, digest_path)
    assert "Simple text diff" in report
    assert "OpenClaw: alpha" in report
    assert "Hermes: beta" in report


def test_build_report_single_provider_run_reports_real_status(tmp_path):
    """A normal (non-benchmark) run must report the actual summary outcome,
    not a misleading 'both providers failed'."""
    digest = {
        "d": "2026-07-31",
        "g": "2026-07-31T17:01:17",
        "summary": {"simple": "Real summary text"},
        "metrics": {"summary": {"source": "hermes", "generated": True, "error": None}},
    }
    digest_path = tmp_path / "digest.json"
    digest_path.write_text(json.dumps(digest), encoding="utf-8")
    report = build_report(digest, digest_path)
    assert "Generated: True" in report
    assert "Error: none" in report
    assert "Real summary text" in report
    # Must NOT claim a provider failed when there was no benchmark comparison.
    assert "failed" not in report.lower()
