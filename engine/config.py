from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DigestEngineConfig:
    engine: str = "standalone"
    openclaw_stages: tuple[str, ...] = ()
    openclaw_profile: str = "digest"
    openclaw_command: str = ""
    openclaw_on_failure: str = "fail-no-deploy"
    summary_provider: str = "legacy"
    summary_primary: str = "openclaw"
    summary_benchmark: bool = False
    hermes_command: str = "hermes"
    hermes_provider: str = "omniroute"
    hermes_model: str = "codex-combo"

    @property
    def uses_openclaw_summary(self) -> bool:
        return self.summary_provider == "openclaw" or (self.summary_provider == "legacy" and self.engine == "openclaw" and "summary" in self.openclaw_stages)

    @property
    def uses_hermes_summary(self) -> bool:
        return self.summary_provider == "hermes"

    @property
    def uses_benchmark_summary(self) -> bool:
        return self.summary_benchmark or self.summary_provider == "benchmark"


def _split_stages(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())


def default_openclaw_command() -> str:
    research_engine = Path.home() / ".openclaw" / "workspace" / "projects" / "research-engine"
    # The repo normally lives at /Users/rickie/code/ai-digest-reader and research-engine at
    # /Users/rickie/.openclaw/workspace/projects/research-engine. Keep the value overrideable
    # for tests, other machines, and future packaging.
    return f"cd {research_engine} && .venv/bin/python -m research_engine.cli digest-summary"


def load_engine_config(env: dict[str, str] | None = None) -> DigestEngineConfig:
    env = env or os.environ
    engine = (env.get("AI_DIGEST_ENGINE") or "standalone").strip().lower()
    if engine not in {"standalone", "openclaw"}:
        raise ValueError("AI_DIGEST_ENGINE must be 'standalone' or 'openclaw'")
    stages = _split_stages(env.get("AI_DIGEST_OPENCLAW_STAGES") or "summary") if engine == "openclaw" else ()
    unsupported = set(stages) - {"summary", "notebooklm_ingest"}
    if unsupported:
        raise ValueError(f"Unsupported AI_DIGEST_OPENCLAW_STAGES: {', '.join(sorted(unsupported))}")
    summary_provider = (env.get("AI_DIGEST_SUMMARY_PROVIDER") or "hermes").strip().lower()
    if summary_provider not in {"legacy", "openclaw", "hermes", "benchmark"}:
        raise ValueError("AI_DIGEST_SUMMARY_PROVIDER must be 'legacy', 'openclaw', 'hermes', or 'benchmark'")
    summary_benchmark = (env.get("AI_DIGEST_SUMMARY_BENCHMARK") or "0").strip() == "1"
    return DigestEngineConfig(
        engine=engine,
        openclaw_stages=stages,
        openclaw_profile=(env.get("AI_DIGEST_OPENCLAW_PROFILE") or "digest").strip(),
        openclaw_command=(env.get("AI_DIGEST_OPENCLAW_COMMAND") or default_openclaw_command()).strip(),
        openclaw_on_failure=(env.get("AI_DIGEST_OPENCLAW_ON_FAILURE") or "fail-no-deploy").strip(),
        summary_provider=summary_provider,
        summary_primary=(env.get("AI_DIGEST_SUMMARY_PRIMARY") or "openclaw").strip().lower(),
        summary_benchmark=summary_benchmark,
        hermes_command=(env.get("AI_DIGEST_HERMES_COMMAND") or "hermes").strip(),
        hermes_provider=(env.get("AI_DIGEST_HERMES_PROVIDER") or "omniroute").strip(),
        hermes_model=(env.get("AI_DIGEST_HERMES_MODEL") or "codex-combo").strip(),
    )


def render_preflight(config: DigestEngineConfig) -> str:
    credential_source = "openclaw_explicit" if config.engine == "openclaw" else "project_env_or_none"
    stages = ",".join(config.openclaw_stages) if config.openclaw_stages else "local"
    summary_mode = (
        "benchmark"
        if config.uses_benchmark_summary
        else config.summary_provider
    )
    return (
        "AI Digest engine preflight:\n"
        f"  - engine: {config.engine}\n"
        f"  - stages: {stages}\n"
        f"  - summary provider: {summary_mode}\n"
        f"  - hermes model: {config.hermes_model if summary_mode in {'hermes', 'benchmark'} else 'n/a'}\n"
        f"  - profile: {config.openclaw_profile if config.engine == 'openclaw' else 'n/a'}\n"
        f"  - credential source category: {credential_source}\n"
        f"  - failure policy: {config.openclaw_on_failure if config.engine == 'openclaw' else 'standalone default'}"
    )
