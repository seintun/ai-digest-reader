from engine.config import load_engine_config, render_preflight


def test_load_engine_config_defaults_to_standalone():
    config = load_engine_config({})
    assert config.engine == "standalone"
    assert config.openclaw_stages == ()
    assert config.summary_provider == "legacy"
    assert "summary provider: legacy" in render_preflight(config)


def test_load_engine_config_openclaw_summary_is_explicit():
    config = load_engine_config({"AI_DIGEST_ENGINE": "openclaw", "AI_DIGEST_OPENCLAW_STAGES": "summary"})
    assert config.engine == "openclaw"
    assert config.uses_openclaw_summary
    assert config.summary_provider == "openclaw"
    assert "summary provider: openclaw" in render_preflight(config)
    assert "credential source category: openclaw_explicit" in render_preflight(config)


def test_load_engine_config_hermes_provider_is_supported():
    config = load_engine_config({"AI_DIGEST_SUMMARY_PROVIDER": "hermes", "AI_DIGEST_HERMES_MODEL": "codex-combo"})
    assert config.summary_provider == "hermes"
    assert config.uses_hermes_summary
    assert config.hermes_model == "codex-combo"
    assert "summary provider: hermes" in render_preflight(config)


def test_load_engine_config_benchmark_mode_is_supported():
    config = load_engine_config({"AI_DIGEST_SUMMARY_PROVIDER": "benchmark", "AI_DIGEST_SUMMARY_PRIMARY": "hermes"})
    assert config.uses_benchmark_summary
    assert config.summary_provider == "benchmark"
    assert "summary provider: benchmark" in render_preflight(config)
    assert "hermes model: codex-combo" in render_preflight(config)


def test_load_engine_config_openclaw_notebooklm_ingest_stage_is_supported():
    config = load_engine_config({"AI_DIGEST_ENGINE": "openclaw", "AI_DIGEST_OPENCLAW_STAGES": "summary,notebooklm_ingest"})
    assert config.engine == "openclaw"
    assert config.openclaw_stages == ("summary", "notebooklm_ingest")
    assert config.uses_openclaw_summary


def test_load_engine_config_rejects_unknown_stage():
    try:
        load_engine_config({"AI_DIGEST_ENGINE": "openclaw", "AI_DIGEST_OPENCLAW_STAGES": "rank"})
    except ValueError as exc:
        assert "Unsupported" in str(exc)
    else:
        raise AssertionError("expected ValueError")
