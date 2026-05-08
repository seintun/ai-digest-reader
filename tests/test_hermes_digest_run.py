from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "hermes-digest-run.sh"
DEFAULT_DIGEST = REPO_ROOT / "ai-digest-reader" / "public" / "data" / "digest.json"


def run_script(*args: str, **env_overrides: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(env_overrides)
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )


def parse_summary(stdout: str) -> dict:
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    payload = lines[-1]
    return json.loads(payload)


def test_check_only_mode_validates_existing_digest_and_emits_summary():
    result = run_script("--check-only", AI_DIGEST_DIGEST_PATH=str(DEFAULT_DIGEST))
    assert result.returncode == 0, result.stdout + result.stderr
    summary = parse_summary(result.stdout)
    assert summary["mode"] == "check-only"
    assert summary["phase"] == "check"
    assert summary["status"] == "succeeded"
    assert summary["validated"] is True
    assert summary["built"] is False
    assert summary["pushed"] is False
    assert summary["digest_path"].endswith("ai-digest-reader/public/data/digest.json")


def test_help_shows_usage():
    result = run_script("--help")
    assert result.returncode == 0
    assert "Usage: scripts/hermes-digest-run.sh" in result.stdout
    assert "--check-only" in result.stdout


def test_unknown_argument_fails_fast():
    result = run_script("--definitely-not-a-real-flag")
    assert result.returncode == 2
    assert "unknown argument" in result.stdout
