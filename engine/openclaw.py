from __future__ import annotations

import json
import os
import shlex
import subprocess
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

from schema import validate_summary
from .config import DigestEngineConfig


def validate_grounded_summary(summary: Any, ranked_posts: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    if not validate_summary(summary):
        return False, ["summary does not match schema-v2"]
    ids = {str(post.get("i", "")) for post in ranked_posts}
    urls = {str(post.get("i", "")): str(post.get("u", "")) for post in ranked_posts}
    warnings: list[str] = []
    for item in summary["structured"]["mustRead"]:
        story_id = item.get("id", "")
        if story_id not in ids:
            return False, [f"summary references missing story id: {story_id}"]
        expected_url = urls.get(story_id, "")
        if expected_url and item.get("url") != expected_url:
            warnings.append(f"summary url differs from input for {story_id}")
    return True, warnings


def generate_summary_with_openclaw(ranked_posts: list[dict[str, Any]], config: DigestEngineConfig) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    if not ranked_posts:
        return None, {"source": "openclaw", "generated": False, "error": "no ranked posts"}
    with tempfile.TemporaryDirectory(prefix="ai-digest-openclaw-") as tmp:
        tmp_path = Path(tmp)
        input_path = tmp_path / "ranked-posts.json"
        output_path = tmp_path / "summary.json"
        metrics_path = tmp_path / "metrics.json"
        input_path.write_text(json.dumps(ranked_posts[:15]), encoding="utf-8")
        command = (
            f"{config.openclaw_command} "
            f"--profile {shlex.quote(config.openclaw_profile)} "
            f"--input {shlex.quote(str(input_path))} "
            f"--output {shlex.quote(str(output_path))} "
            f"--metrics-json {shlex.quote(str(metrics_path))}"
        )
        completed = subprocess.run(command, shell=True, text=True, capture_output=True, timeout=120)
        if completed.returncode != 0:
            return None, {
                "source": "openclaw",
                "generated": False,
                "error": completed.stderr.strip() or completed.stdout.strip() or f"exit {completed.returncode}",
            }
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        summary = payload.get("summary")
        valid, warnings = validate_grounded_summary(summary, ranked_posts[:15])
        if not valid:
            return None, {"source": "openclaw", "generated": False, "error": "; ".join(warnings)}
        metrics = payload.get("metrics", {}) if isinstance(payload, dict) else {}
        return summary, {"source": "openclaw", "generated": True, "usage": {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "cost_source": "openclaw_metrics"}, "openclaw": metrics, "validation_warnings": warnings}


def ingest_digest_into_notebooklm(digest: dict[str, Any], config: DigestEngineConfig, dry_run: bool = False) -> dict[str, Any]:
    """Ingest ranked digest links into a daily NotebookLM notebook.

    Note: Requires `notebooklm login` to be completed previously. Dry-run bypasses auth.
    """
    posts = digest.get("r", []) + digest.get("h", []) + digest.get("rs", [])
    if not posts:
        return {"error": "no posts to ingest", "notebook_id": None, "notebook_url": None}
    with tempfile.TemporaryDirectory(prefix="digest-notebooklm-") as tmp:
        tmp_path = Path(tmp)
        input_path = tmp_path / "posts.json"
        output_path = tmp_path / "ingest-report.json"
        input_path.write_text(json.dumps(posts), encoding="utf-8")
        research_engine_root = Path.home() / ".openclaw" / "workspace" / "projects" / "research-engine"
        if not research_engine_root.exists():
            return {"error": f"research-engine not found at {research_engine_root}", "notebook_id": None, "notebook_url": None}
        # Build command to call research-engine's notebooklm-ingest CLI
        cmd = (
            f"cd {research_engine_root} && .venv/bin/python -m research_engine.cli notebooklm-ingest "
            f"--input {shlex.quote(str(input_path))} "
            f"--output {shlex.quote(str(output_path))} "
            f"--max-sources 100"
        )
        if dry_run:
            cmd += " --dry-run"
        completed = subprocess.run(cmd, shell=True, text=True, capture_output=True, timeout=900)
        if completed.returncode != 0:
            return {
                "error": "notebooklm-ingest command failed",
                "exit_code": completed.returncode,
                "stderr": completed.stderr.strip(),
                "stdout": completed.stdout.strip(),
                "notebook_id": None,
                "notebook_url": None,
            }
        try:
            report = json.loads(output_path.read_text(encoding="utf-8"))
        except Exception as e:
            return {"error": f"Failed to parse ingestion report: {e}", "notebook_id": None, "notebook_url": None}
        return report
