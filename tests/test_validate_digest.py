from __future__ import annotations

import json

from scripts.validate_digest import validate_digest_file


def _summary():
    return {
        "schema_version": "2",
        "simple": "A useful summary.",
        "structured": {
            "themes": ["AI", "Tools", "Policy"],
            "breaking": "Story A",
            "mustRead": [
                {"id": "rd-0", "title": "Story A", "url": "https://example.com/a", "reason": "Important."},
                {"id": "hn-0", "title": "Story B", "url": "https://example.com/b", "reason": "Important."},
                {"id": "rs-0", "title": "Story C", "url": "https://example.com/c", "reason": "Important."},
            ],
        },
        "fullBrief": {
            "intro": "Intro.",
            "sections": [{"heading": "A", "body": "Body."}, {"heading": "B", "body": "Body."}],
            "closing": "Close.",
        },
    }


def _digest(summary=True):
    data = {
        "v": 4,
        "d": "2026-04-25",
        "g": "2026-04-25T00:00:00",
        "r": [{"i": "rd-0", "t": "Story A", "u": "https://example.com/a"}],
        "h": [{"i": "hn-0", "t": "Story B", "u": "https://example.com/b"}],
        "rs": [{"i": "rs-0", "t": "Story C", "u": "https://example.com/c"}],
    }
    if summary:
        data["summary"] = _summary()
    return data


def test_validate_digest_file_accepts_grounded_summary(tmp_path):
    path = tmp_path / "digest.json"
    path.write_text(json.dumps(_digest()))
    ok, errors = validate_digest_file(str(path), require_summary=True)
    assert ok
    assert errors == []


def test_validate_digest_file_rejects_missing_required_summary(tmp_path):
    path = tmp_path / "digest.json"
    path.write_text(json.dumps(_digest(summary=False)))
    ok, errors = validate_digest_file(str(path), require_summary=True)
    assert not ok
    assert "summary is required" in errors[0]


def test_validate_digest_file_rejects_invented_must_read_id(tmp_path):
    digest = _digest()
    digest["summary"]["structured"]["mustRead"][0]["id"] = "fake-1"
    path = tmp_path / "digest.json"
    path.write_text(json.dumps(digest))
    ok, errors = validate_digest_file(str(path), require_summary=True)
    assert not ok
    assert "fake-1" in errors[0]
