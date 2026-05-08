from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "hermes-digest-run.sh"
VALID_DIGEST = json.dumps(
    {
        "schema_version": "2",
        "simple": "ok",
        "structured": {
            "themes": ["a", "b", "c"],
            "breaking": "x",
            "mustRead": [
                {"id": "1", "title": "t", "url": "https://example.com", "reason": "r"},
                {"id": "2", "title": "t2", "url": "https://example.org", "reason": "r2"},
                {"id": "3", "title": "t3", "url": "https://example.net", "reason": "r3"},
            ],
        },
        "fullBrief": {
            "intro": "i",
            "sections": [
                {"heading": "h1", "body": "b1"},
                {"heading": "h2", "body": "b2"},
            ],
            "closing": "c",
        },
    }
)


def run_script(*args: str, cwd: Path = REPO_ROOT, **env_overrides: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(env_overrides)
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=300,
    )


def parse_summary(stdout: str) -> dict:
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    return json.loads(lines[-1])


def make_sandbox(tmp_path: Path) -> Path:
    sandbox = tmp_path / "sandbox"
    (sandbox / "scripts").mkdir(parents=True)
    (sandbox / ".venv" / "bin").mkdir(parents=True)
    (sandbox / "output" / "2026-05-07").mkdir(parents=True)
    (sandbox / "ai-digest-reader" / "public" / "data").mkdir(parents=True)

    shutil.copy2(REPO_ROOT / "scripts" / "hermes-digest-run.sh", sandbox / "scripts" / "hermes-digest-run.sh")
    os.chmod(sandbox / "scripts" / "hermes-digest-run.sh", 0o755)

    (sandbox / ".venv" / "bin" / "python").write_text("#!/usr/bin/env bash\nexec python3 \"$@\"\n", encoding="utf-8")
    os.chmod(sandbox / ".venv" / "bin" / "python", 0o755)

    (sandbox / "scripts" / "generate-and-deploy.sh").write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "mkdir -p output/2026-05-07\n"
        f"printf '%s\\n' '{VALID_DIGEST}' > output/2026-05-07/digest.json\n"
        "echo stub generate-and-deploy\n",
        encoding="utf-8",
    )
    os.chmod(sandbox / "scripts" / "generate-and-deploy.sh", 0o755)

    (sandbox / "scripts" / "validate-digest.py").write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "print(f'validated {sys.argv[1]}')\n",
        encoding="utf-8",
    )
    os.chmod(sandbox / "scripts" / "validate-digest.py", 0o755)

    return sandbox


def test_check_only_mode_validates_existing_digest_and_emits_summary(tmp_path):
    sandbox = make_sandbox(tmp_path)
    digest = sandbox / "ai-digest-reader" / "public" / "data" / "digest.json"
    digest.write_text(VALID_DIGEST, encoding="utf-8")

    result = subprocess.run(
        ["bash", str(sandbox / "scripts" / "hermes-digest-run.sh"), "--check-only"],
        cwd=sandbox,
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    summary = parse_summary(result.stdout)
    assert summary["mode"] == "check-only"
    assert summary["phase"] == "check"
    assert summary["status"] == "succeeded"
    assert summary["validated"] is True
    assert summary["built"] is False
    assert summary["pushed"] is False
    assert summary["digest_path"].endswith("ai-digest-reader/public/data/digest.json")


def test_validate_only_mode_runs_generation_without_build_or_push(tmp_path):
    sandbox = make_sandbox(tmp_path)
    result = subprocess.run(
        ["bash", str(sandbox / "scripts" / "hermes-digest-run.sh"), "--validate-only"],
        cwd=sandbox,
        env={
            **os.environ,
            "PATH": os.environ.get("PATH", ""),
            "AI_DIGEST_REQUIRE_SUMMARY": "0",
            "AI_DIGEST_DEPLOY_MODE": "validate-only",
        },
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    summary = parse_summary(result.stdout)
    assert summary["mode"] == "validate-only"
    assert summary["phase"] == "generate"
    assert summary["status"] == "succeeded"
    assert summary["validated"] is True
    assert summary["built"] is False
    assert summary["pushed"] is False
    assert summary["digest_path"].endswith("output/2026-05-07/digest.json")


def test_full_mode_runs_generation_and_marks_build_push_complete(tmp_path):
    sandbox = make_sandbox(tmp_path)
    result = subprocess.run(
        ["bash", str(sandbox / "scripts" / "hermes-digest-run.sh"), "--full"],
        cwd=sandbox,
        env={
            **os.environ,
            "PATH": os.environ.get("PATH", ""),
            "AI_DIGEST_REQUIRE_SUMMARY": "0",
            "AI_DIGEST_OPENCLAW_STAGES": "summary",
            "AI_DIGEST_DEPLOY_MODE": "full",
        },
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    summary = parse_summary(result.stdout)
    assert summary["mode"] == "full"
    assert summary["phase"] == "generate"
    assert summary["status"] == "succeeded"
    assert summary["validated"] is True
    assert summary["built"] is True
    assert summary["pushed"] is True
    assert summary["digest_path"].endswith("output/2026-05-07/digest.json")


def test_help_shows_usage():
    result = run_script("--help")
    assert result.returncode == 0
    assert "Usage: scripts/hermes-digest-run.sh" in result.stdout
    assert "--check-only" in result.stdout
    assert "--validate-only" in result.stdout
    assert "--full" in result.stdout


def test_unknown_argument_fails_fast():
    result = run_script("--definitely-not-a-real-flag")
    assert result.returncode == 2
    assert "unknown argument" in result.stdout
