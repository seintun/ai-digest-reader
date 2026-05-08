from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _must_read_ids(summary: dict[str, Any] | None) -> list[str]:
    if not summary:
        return []
    structured = summary.get("structured") or {}
    items = structured.get("mustRead") or []
    ids: list[str] = []
    for item in items:
        story_id = str(item.get("id", "")).strip()
        if story_id:
            ids.append(story_id)
    return ids


def _summary_text(summary: dict[str, Any] | None) -> str:
    if not summary:
        return ""
    return str(summary.get("simple", "")).strip()


def build_report(digest: dict[str, Any], digest_path: Path) -> str:
    metrics = digest.get("metrics") or {}
    summary_meta = metrics.get("summary") or {}
    benchmark = summary_meta.get("benchmark") or {}
    openclaw = benchmark.get("openclaw") or {}
    hermes = benchmark.get("hermes") or {}
    selected = summary_meta.get("source") or "none"

    openclaw_summary = openclaw.get("summary") if isinstance(openclaw, dict) else None
    hermes_summary = hermes.get("summary") if isinstance(hermes, dict) else None
    openclaw_ids = set(_must_read_ids(openclaw_summary if isinstance(openclaw_summary, dict) else None))
    hermes_ids = set(_must_read_ids(hermes_summary if isinstance(hermes_summary, dict) else None))
    overlap = sorted(openclaw_ids & hermes_ids)
    union = sorted(openclaw_ids | hermes_ids)

    def _duration(entry: dict[str, Any]) -> str:
        value = entry.get("duration_seconds")
        return f"{value}s" if value is not None else "n/a"

    def _status(entry: dict[str, Any]) -> str:
        if entry.get("generated"):
            return "generated"
        return f"failed: {entry.get('error', 'unknown error')}"

    date_str = digest.get("d") or digest_path.parent.name
    generated_at = digest.get("g") or "unknown"
    lines = [
        "# AI Digest Hermes/OpenClaw Benchmark Report",
        "",
        f"- Digest date: {date_str}",
        f"- Generated at: {generated_at}",
        f"- Digest file: `{digest_path}`",
        f"- Selected summary source: `{selected}`",
        f"- Benchmark primary: `{benchmark.get('primary', 'unknown')}`",
        "",
        "## Provider results",
        f"- OpenClaw: {_status(openclaw)} ({_duration(openclaw)})",
        f"- Hermes: {_status(hermes)} ({_duration(hermes)})",
        "",
        "## Comparison",
        f"- OpenClaw must-read IDs: {', '.join(sorted(openclaw_ids)) or 'none'}",
        f"- Hermes must-read IDs: {', '.join(sorted(hermes_ids)) or 'none'}",
        f"- Overlap: {len(overlap)} / union {len(union)}",
        f"- Overlap IDs: {', '.join(overlap) or 'none'}",
        "",
        "## Selected summary",
        f"- Simple text: {_summary_text(digest.get('summary') if isinstance(digest.get('summary'), dict) else None) or 'none'}",
    ]

    if isinstance(openclaw_summary, dict) and isinstance(hermes_summary, dict):
        openclaw_simple = _summary_text(openclaw_summary)
        hermes_simple = _summary_text(hermes_summary)
        if openclaw_simple != hermes_simple:
            lines.extend([
                "",
                "## Simple text diff",
                "- OpenClaw simple summary differs from Hermes simple summary.",
                f"- OpenClaw: {openclaw_simple or 'none'}",
                f"- Hermes: {hermes_simple or 'none'}",
            ])

    lines.extend([
        "",
        "## Notes",
        "- This report is generated from the benchmark metadata embedded in the digest artifact.",
        "- Use it as the daily artifact for the 7-day migration comparison.",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Write a daily AI Digest benchmark report")
    parser.add_argument("digest_path", type=Path)
    parser.add_argument("report_path", type=Path)
    args = parser.parse_args()

    digest = json.loads(args.digest_path.read_text(encoding="utf-8"))
    report = build_report(digest, args.digest_path)
    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    args.report_path.write_text(report, encoding="utf-8")
    print(args.report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
