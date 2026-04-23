"""Unified LLM client with session reuse, caching, retry, and CLI fallback."""
import hashlib
import os
import subprocess
import time
from typing import Optional

import requests

from model_pricing import usage_to_dict

_DEFAULT_MODEL = "moonshotai/kimi-k2.6"
_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
_HEADERS_BASE = {
    "HTTP-Referer": "https://dailydigest.vercel.app",
    "X-Title": "DailyDigest",
}


class LLMClient:
    def __init__(
        self,
        model: str = None,
        api_key: str = None,
        connect_timeout: float = None,
        read_timeout: float = None,
        cli_timeout: int = None,
    ):
        self._model = model or os.environ.get("OPENROUTER_MODEL", _DEFAULT_MODEL)
        self._api_key = api_key if api_key is not None else os.environ.get("OPENROUTER_API_KEY")
        self._connect_timeout = connect_timeout if connect_timeout is not None else float(
            os.environ.get("SUMMARY_AI_CONNECT_TIMEOUT", "10") or "10"
        )
        self._read_timeout = read_timeout if read_timeout is not None else float(
            os.environ.get("SUMMARY_AI_READ_TIMEOUT", "75") or "75"
        )
        self._cli_timeout = cli_timeout if cli_timeout is not None else int(
            os.environ.get("CLAUDE_CLI_TIMEOUT_SECONDS", "60") or "60"
        )
        self._session = requests.Session()
        self._cache: dict = {}

    def complete(self, prompt: str, system: str = None) -> tuple[Optional[str], dict]:
        """
        Call the LLM with prompt and optional system message.
        Returns (content_str_or_None, usage_dict).
        Tries OpenRouter first (with one retry on failure, 2s backoff),
        then falls back to Claude CLI.
        Caches successful responses by content hash to avoid duplicate API calls.
        """
        cache_key = hashlib.sha256(((system or "") + prompt).encode()).hexdigest()
        if cache_key in self._cache:
            return (self._cache[cache_key], usage_to_dict(0, 0))

        if self._api_key:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            body = {"model": self._model, "messages": messages}
            headers = {
                **_HEADERS_BASE,
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            }

            for attempt in range(2):
                print(f"  llm call (attempt {attempt + 1}/2, {self._model})...", flush=True)
                try:
                    resp = self._session.post(
                        _OPENROUTER_URL,
                        json=body,
                        headers=headers,
                        timeout=(self._connect_timeout, self._read_timeout),
                    )
                    resp.raise_for_status()
                    payload = resp.json()
                    if payload.get("error"):
                        raise RuntimeError(str(payload.get("error")))
                    usage = payload.get("usage", {}) or {}
                    input_tokens = int(usage.get("prompt_tokens", 0) or 0)
                    output_tokens = int(usage.get("completion_tokens", 0) or 0)
                    usage_dict = usage_to_dict(
                        input_tokens,
                        output_tokens,
                        openrouter_usage=usage,
                        cost_source="openrouter_usage",
                    )
                    usage_dict["total_tokens"] = int(
                        usage.get("total_tokens", input_tokens + output_tokens)
                    )
                    choices = payload.get("choices", [])
                    content = (
                        ((choices[0] or {}).get("message") or {}).get("content") or ""
                        if choices
                        else ""
                    )
                    if content:
                        self._cache[cache_key] = content
                        return (content, usage_dict)
                    return (None, usage_dict)
                except Exception as e:
                    print(f"OpenRouter API error: {e}")
                    if attempt == 0:
                        time.sleep(2)

        return self._cli_fallback(prompt, cache_key)

    def _cli_fallback(self, prompt: str, cache_key: str) -> tuple[Optional[str], dict]:
        try:
            result = subprocess.run(
                ["claude", "--print", prompt],
                capture_output=True,
                text=True,
                timeout=self._cli_timeout,
            )
            content = result.stdout.strip() or None
            if content:
                self._cache[cache_key] = content
            return (content, usage_to_dict(0, 0))
        except FileNotFoundError:
            print("Warning: claude CLI not found")
            return (None, usage_to_dict(0, 0))
        except subprocess.TimeoutExpired:
            print("Warning: claude CLI timed out")
            return (None, usage_to_dict(0, 0))
        except Exception as e:
            print(f"Warning: claude CLI error: {e}")
            return (None, usage_to_dict(0, 0))


def create_client(**kwargs) -> LLMClient:
    """Create an LLMClient with default env-based config."""
    return LLMClient(**kwargs)
