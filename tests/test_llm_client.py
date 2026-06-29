"""Tests for llm_client.LLMClient."""
import hashlib
from unittest.mock import MagicMock, patch

import requests

from llm_client import LLMClient


def _make_mock_response(content="test content", prompt_tokens=100, completion_tokens=50):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "choices": [{"message": {"content": content}}],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }
    return mock_response


def _cache_key(prompt, system=None, max_tokens=None, temperature=None):
    return hashlib.sha256(
        "\0".join([
            system or "",
            prompt,
            "" if max_tokens is None else str(max_tokens),
            "" if temperature is None else str(temperature),
        ]).encode()
    ).hexdigest()


def ***REDACTED_RUBYGEMS_KEY***():
    client = LLMClient(api_key="test-key")
    prompt = "hello"
    key = _cache_key(prompt)
    client._cache[key] = "cached response"

    with patch.object(client._session, "post") as mock_post:
        content, usage = client.complete(prompt)

    mock_post.assert_not_called()
    assert content == "cached response"


def ***REDACTED_RUBYGEMS_KEY***():
    client = LLMClient(api_key="test-key")
    with patch.object(client._session, "post", ***REDACTED_RUBYGEMS_KEY***("hello world")):
        content, usage = client.complete("test prompt")

    assert content == "hello world"
    assert usage["input_tokens"] == 100
    assert usage["output_tokens"] == 50


def ***REDACTED_RUBYGEMS_KEY***():
    client = LLMClient(api_key="test-key")
    success_response = _make_mock_response("retry success")
    call_count = 0

    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("transient error")
        return success_response

    with patch.object(client._session, "post", side_effect=side_effect):
        with patch("llm_client.time.sleep"):  # skip the sleep
            content, usage = client.complete("test prompt")

    assert content == "retry success"
    assert call_count == 2


def ***REDACTED_RUBYGEMS_KEY***():
    client = LLMClient(api_key="test-key")

    cli_result = MagicMock()
    cli_result.stdout = "cli output"
    cli_result.returncode = 0

    with patch.object(client._session, "post", ***REDACTED_RUBYGEMS_KEY***("api down")):
        with patch("llm_client.time.sleep"):
            with patch("llm_client.subprocess.run", ***REDACTED_RUBYGEMS_KEY***):
                content, usage = client.complete("test prompt")

    assert content == "cli output"


def ***REDACTED_RUBYGEMS_KEY***():
    client = LLMClient(api_key="test-key")

    with patch.object(client._session, "post", ***REDACTED_RUBYGEMS_KEY***("api down")):
        with patch("llm_client.time.sleep"):
            with patch("llm_client.subprocess.run", ***REDACTED_RUBYGEMS_KEY***):
                content, usage = client.complete("test prompt")

    assert content is None


def ***REDACTED_RUBYGEMS_KEY***():
    client = LLMClient(api_key="")

    cli_result = MagicMock()
    cli_result.stdout = "cli only output"
    cli_result.returncode = 0

    with patch.object(client._session, "post") as mock_post:
        with patch("llm_client.subprocess.run", ***REDACTED_RUBYGEMS_KEY***):
            content, usage = client.complete("test prompt")

    mock_post.assert_not_called()
    assert content == "cli only output"


def ***REDACTED_RUBYGEMS_KEY***():
    client = LLMClient(api_key="test-key")
    captured_body = {}

    def capture_post(*args, **kwargs):
        captured_body.update(kwargs.get("json", {}))
        return _make_mock_response()

    with patch.object(client._session, "post", ***REDACTED_RUBYGEMS_KEY***):
        client.complete("user prompt", system="You are helpful")

    messages = captured_body.get("messages", [])
    assert any(m.get("role") == "system" and "helpful" in m.get("content", "") for m in messages)
    assert any(m.get("role") == "user" for m in messages)


def ***REDACTED_RUBYGEMS_KEY***():
    client = LLMClient(api_key="test-key")
    captured_body = {}

    def capture_post(*args, **kwargs):
        captured_body.update(kwargs.get("json", {}))
        return _make_mock_response()

    with patch.object(client._session, "post", ***REDACTED_RUBYGEMS_KEY***):
        client.complete("user prompt", max_tokens=123, temperature=0)

    assert captured_body["max_tokens"] == 123
    assert captured_body["temperature"] == 0


def ***REDACTED_RUBYGEMS_KEY***():
    client = LLMClient(api_key="test-key")
    client._cache[_cache_key("user prompt")] = "uncapped cached"

    with patch.object(client._session, "post", ***REDACTED_RUBYGEMS_KEY***("capped response")) as post:
        content, _usage = client.complete("user prompt", max_tokens=123, temperature=0)

    assert content == "capped response"
    assert post.call_count == 1


def ***REDACTED_RUBYGEMS_KEY***():
    client = LLMClient(api_key="test-key")
    error = requests.HTTPError("403 Client Error")
    error.response = MagicMock(status_code=403)
    response = MagicMock()
    response.raise_for_status.side_effect = error

    with patch.object(client._session, "post", ***REDACTED_RUBYGEMS_KEY***) as post:
        with patch("llm_client.time.sleep") as sleep:
            with patch("llm_client.subprocess.run") as cli:
                content, usage = client.complete("test prompt")

    assert content is None
    assert usage["cost_source"] == "openrouter_http_403"
    assert post.call_count == 1
    sleep.assert_not_called()
    cli.assert_not_called()
