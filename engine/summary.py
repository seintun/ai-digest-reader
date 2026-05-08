from __future__ import annotations

import shlex
import subprocess
import time
from typing import Any, Dict, List, Optional

from analyzer_v2 import _SYSTEM_PROMPT, _build_prompt, generate_summary_with_meta as legacy_generate_summary_with_meta
from model_pricing import usage_to_dict
from schema import parse_llm_json, validate_summary
from .config import DigestEngineConfig
from .openclaw import generate_summary_with_openclaw, validate_grounded_summary


def _hermes_command(config: DigestEngineConfig, prompt: str) -> tuple[Optional[str], Dict[str, Any]]:
    cmd = [*shlex.split(config.hermes_command), "chat", "-Q", "--provider", config.hermes_provider, "--model", config.hermes_model, "-q", prompt]
    started = time.perf_counter()
    try:
        completed = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except FileNotFoundError:
        return None, {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "cost_source": "hermes_cli_missing", "command": cmd[0] if cmd else config.hermes_command, "duration_seconds": round(time.perf_counter() - started, 3)}
    except subprocess.TimeoutExpired:
        return None, {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "cost_source": "hermes_cli_timeout", "command": cmd[0] if cmd else config.hermes_command, "duration_seconds": round(time.perf_counter() - started, 3)}
    duration = round(time.perf_counter() - started, 3)
    if completed.returncode != 0:
        return None, {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "cost_source": "hermes_cli_error", "stderr": completed.stderr.strip(), "stdout": completed.stdout.strip(), "duration_seconds": duration}
    content = (completed.stdout or "").strip() or None
    return content, {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0, "cost_source": "hermes_cli", "duration_seconds": duration}


def generate_summary_with_hermes(ranked_posts: List[Dict[str, Any]], config: DigestEngineConfig) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    if not ranked_posts:
        return None, {"source": "hermes", "generated": False, "error": "no ranked posts"}

    prompt = _SYSTEM_PROMPT + "\n\n" + _build_prompt(ranked_posts)
    content, usage = _hermes_command(config, prompt)
    if not content:
        return None, {"source": "hermes", "generated": False, "error": usage.get("stderr") or usage.get("cost_source") or "hermes returned no content", "usage": usage}

    parsed = parse_llm_json(content)
    if not parsed or not validate_summary(parsed):
        return None, {"source": "hermes", "generated": False, "error": "Hermes output did not validate against schema-v2", "usage": usage}

    valid, warnings = validate_grounded_summary(parsed, ranked_posts[:15])
    if not valid:
        return None, {"source": "hermes", "generated": False, "error": "; ".join(warnings), "usage": usage}

    return parsed, {"source": "hermes", "generated": True, "usage": usage, "validation_warnings": warnings}


def _choose_primary(config: DigestEngineConfig, openclaw_ok: bool, hermes_ok: bool) -> str:
    primary = (config.summary_primary or "openclaw").strip().lower()
    if primary == "hermes" and hermes_ok:
        return "hermes"
    if primary == "openclaw" and openclaw_ok:
        return "openclaw"
    if openclaw_ok:
        return "openclaw"
    if hermes_ok:
        return "hermes"
    return "openclaw"


def generate_summary_with_provider(ranked_posts: List[Dict[str, Any]], config: DigestEngineConfig) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    if config.uses_benchmark_summary:
        openclaw_summary, openclaw_meta = generate_summary_with_openclaw(ranked_posts, config)
        hermes_summary, hermes_meta = generate_summary_with_hermes(ranked_posts, config)
        primary = _choose_primary(config, bool(openclaw_summary), bool(hermes_summary))
        selected_summary = openclaw_summary if primary == "openclaw" else hermes_summary
        if selected_summary is None:
            selected_summary = openclaw_summary or hermes_summary
        def _bench(meta: dict[str, Any], summary: dict[str, Any] | None) -> dict[str, Any]:
            return {
                "generated": bool(summary),
                "error": meta.get("error"),
                "source": meta.get("source"),
                "duration_seconds": meta.get("duration_seconds"),
                "summary": summary,
                "meta": meta,
            }

        selected_meta = {
            "source": primary if selected_summary else "none",
            "generated": bool(selected_summary),
            "usage": usage_to_dict(0, 0),
            "benchmark": {
                "primary": primary,
                "openclaw": _bench(openclaw_meta, openclaw_summary),
                "hermes": _bench(hermes_meta, hermes_summary),
            },
        }
        return selected_summary, selected_meta

    if config.uses_hermes_summary:
        return generate_summary_with_hermes(ranked_posts, config)
    if config.uses_openclaw_summary:
        return generate_summary_with_openclaw(ranked_posts, config)
    return legacy_generate_summary_with_meta(ranked_posts)
