from engine.config import load_engine_config, render_preflight


def test_load_engine_config_defaults_to_standalone():
    config = load_engine_config({})
    assert config.engine == "standalone"
    assert config.openclaw_stages == ()
    assert "engine: standalone" in render_preflight(config)


def test_load_engine_config_openclaw_summary_is_explicit():
    config = load_engine_config({"AI_DIGEST_ENGINE": "openclaw", "AI_DIGEST_OPENCLAW_STAGES": "summary"})
    assert config.engine == "openclaw"
    assert config.uses_openclaw_summary
    assert "credential source category: openclaw_explicit" in render_preflight(config)


def test_load_engine_config_rejects_unknown_stage():
    try:
        load_engine_config({"AI_DIGEST_ENGINE": "openclaw", "AI_DIGEST_OPENCLAW_STAGES": "rank"})
    except ValueError as exc:
        assert "Unsupported" in str(exc)
    else:
        raise AssertionError("expected ValueError")
