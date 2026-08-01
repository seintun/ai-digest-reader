#!/usr/bin/env python3
"""Quality-regression gate for the AI Digest pipeline.

Reads a freshly generated digest, checks two health signals, and maintains a
small state file so it can detect *repeated* failures across runs:

1. Scrape success rate — the % of URLs we actually attempted to scrape that
   returned content. If it drops below a threshold (default 50%), extraction is
   degrading (sites blocking us, extractors failing). Warn. This is the
   actionable signal. (Note: we do NOT threshold on overall content coverage,
   which is structurally low because most RSS/Reddit items are intentionally not
   scrape candidates.)
2. Summary availability — if the summary is missing/invalid for N consecutive
   runs (default 2), warn. A single failure is tolerated (transient LLM error).

The gate never blocks the pipeline; it returns warnings that the caller (the
Hermes cron wrapper) surfaces to Discord. State is persisted as JSON so the
consecutive-failure counter survives between runs.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Allow running directly from scripts/ while importing repo-root modules.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from schema import validate_summary

DEFAULT_SCRAPE_SUCCESS_THRESHOLD = 50.0
DEFAULT_FAILURE_STREAK = 2
DEFAULT_STATE_PATH = "output/quality-gate-state.json"


def check_quality(
    *,
    scrape_success_rate: float,
    scrape_candidate_urls: int,
    summary_present: bool,
    summary_valid: bool,
    prev_state: dict[str, Any],
    scrape_success_threshold: float = DEFAULT_SCRAPE_SUCCESS_THRESHOLD,
    failure_streak: int = DEFAULT_FAILURE_STREAK,
) -> tuple[list[str], dict[str, Any]]:
    """Evaluate one run. Returns (warnings, new_state)."""
    warnings: list[str] = []

    # Only judge scrape health when we actually attempted to scrape something;
    # a run with zero candidates (e.g. all cache) has nothing to warn about.
    if scrape_candidate_urls > 0 and scrape_success_rate < scrape_success_threshold:
        warnings.append(
            f"Quality gate: scrape success {scrape_success_rate}% is below "
            f"{scrape_success_threshold}% ({scrape_candidate_urls} candidate URLs) — "
            f"extraction is degrading; check extractor fallthroughs."
        )

    summary_ok = summary_present and summary_valid
    consecutive = int(prev_state.get("consecutive_summary_failures", 0) or 0)
    if summary_ok:
        consecutive = 0
    else:
        consecutive += 1
        if consecutive >= failure_streak:
            warnings.append(
                f"Quality gate: summary missing/invalid for {consecutive} consecutive runs "
                f"(threshold {failure_streak}). Investigate the summary provider."
            )

    new_state = {
        "consecutive_summary_failures": consecutive,
        "last_scrape_success_rate": scrape_success_rate,
        "last_summary_ok": summary_ok,
    }
    return warnings, new_state


def evaluate_digest_file(
    path: str,
    *,
    prev_state: dict[str, Any] | None = None,
    scrape_success_threshold: float = DEFAULT_SCRAPE_SUCCESS_THRESHOLD,
    failure_streak: int = DEFAULT_FAILURE_STREAK,
) -> tuple[list[str], dict[str, Any]]:
    """Read a digest JSON and run the quality checks."""
    prev_state = prev_state or {}
    try:
        digest = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        return [f"Quality gate: could not read digest JSON: {exc}"], prev_state

    quality = (digest.get("metrics") or {}).get("quality") or {}
    scrape_success_rate = float(quality.get("scrape_success_rate", 0.0) or 0.0)
    scrape_candidate_urls = int(quality.get("scrape_candidate_urls", 0) or 0)

    summary = digest.get("summary")
    summary_present = bool(summary)
    summary_valid = bool(summary) and validate_summary(summary)

    return check_quality(
        scrape_success_rate=scrape_success_rate,
        scrape_candidate_urls=scrape_candidate_urls,
        summary_present=summary_present,
        summary_valid=summary_valid,
        prev_state=prev_state,
        scrape_success_threshold=scrape_success_threshold,
        failure_streak=failure_streak,
    )


def load_state(path: str) -> dict[str, Any]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_state(path: str, state: dict[str, Any]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="AI Digest quality-regression gate")
    parser.add_argument("path", help="path to digest.json")
    parser.add_argument("--state-path", default=DEFAULT_STATE_PATH)
    parser.add_argument("--scrape-success-threshold", type=float, default=DEFAULT_SCRAPE_SUCCESS_THRESHOLD)
    parser.add_argument("--failure-streak", type=int, default=DEFAULT_FAILURE_STREAK)
    args = parser.parse_args()

    prev_state = load_state(args.state_path)
    warnings, new_state = evaluate_digest_file(
        args.path,
        prev_state=prev_state,
        scrape_success_threshold=args.scrape_success_threshold,
        failure_streak=args.failure_streak,
    )
    save_state(args.state_path, new_state)

    if warnings:
        for warning in warnings:
            print(warning)
        # Exit 2 (distinct from validation's 1) so callers can tell a soft
        # quality warning from a hard validation failure.
        return 2
    print("Quality gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
