"""Tests for the quality-regression gate (evidence coverage + repeated summary failures)."""
import json

from scripts.quality_gate import check_quality, evaluate_digest_file


def test_no_warning_when_healthy():
    warnings, state = check_quality(
        evidence_coverage_pct=65.0,
        summary_present=True,
        summary_valid=True,
        prev_state={},
    )
    assert warnings == []
    assert state["consecutive_summary_failures"] == 0


def test_warns_when_evidence_coverage_below_threshold():
    warnings, state = check_quality(
        evidence_coverage_pct=12.0,
        summary_present=True,
        summary_valid=True,
        prev_state={},
        coverage_threshold=30.0,
    )
    assert any("evidence coverage" in w.lower() for w in warnings)


def test_single_summary_failure_does_not_warn():
    warnings, state = check_quality(
        evidence_coverage_pct=80.0,
        summary_present=False,
        summary_valid=False,
        prev_state={},
    )
    assert warnings == []
    assert state["consecutive_summary_failures"] == 1


def test_two_consecutive_summary_failures_warn():
    warnings, state = check_quality(
        evidence_coverage_pct=80.0,
        summary_present=False,
        summary_valid=False,
        prev_state={"consecutive_summary_failures": 1},
    )
    assert any("summary" in w.lower() for w in warnings)
    assert state["consecutive_summary_failures"] == 2


def test_summary_success_resets_failure_counter():
    warnings, state = check_quality(
        evidence_coverage_pct=80.0,
        summary_present=True,
        summary_valid=True,
        prev_state={"consecutive_summary_failures": 3},
    )
    assert warnings == []
    assert state["consecutive_summary_failures"] == 0


def test_evaluate_digest_file_reads_metrics(tmp_path):
    digest = {
        "v": 4, "d": "2026-07-31", "g": "now",
        "r": [], "h": [{"i": "hn-0", "content": "x"}], "rs": [],
        "summary": {"schema_version": "2", "simple": "s",
                    "structured": {"themes": ["a", "b", "c"], "breaking": "b",
                                   "mustRead": [
                                       {"id": "hn-0", "title": "t", "url": "https://example.com/a", "reason": "r"},
                                       {"id": "hn-0", "title": "t", "url": "https://example.com/b", "reason": "r"},
                                       {"id": "hn-0", "title": "t", "url": "https://example.com/c", "reason": "r"},
                                   ]},
                    "fullBrief": {"intro": "i",
                                  "sections": [{"heading": "h1", "body": "b1"}, {"heading": "h2", "body": "b2"}],
                                  "closing": "c"}},
        "metrics": {"quality": {"evidence_coverage_pct": 55.0}},
    }
    path = tmp_path / "digest.json"
    path.write_text(json.dumps(digest), encoding="utf-8")
    warnings, state = evaluate_digest_file(str(path), prev_state={})
    assert warnings == []
    assert state["consecutive_summary_failures"] == 0
