"""Model pricing helpers for run-cost accounting."""
from __future__ import annotations

from typing import Any, Dict


def estimate_llm_cost_usd(
    input_tokens: int,
    output_tokens: int,
    usd_per_1k_tokens: float | None = None,
    input_usd_per_million_tokens: float | None = None,
    output_usd_per_million_tokens: float | None = None,
) -> float:
    """Static cost estimate when provider/runtime does not report marginal cost."""
    input_tokens = max(0, int(input_tokens or 0))
    output_tokens = max(0, int(output_tokens or 0))
    if input_usd_per_million_tokens is not None or output_usd_per_million_tokens is not None:
        input_rate = max(0.0, float(input_usd_per_million_tokens or 0.0))
        output_rate = max(0.0, float(output_usd_per_million_tokens or 0.0))
        return round((input_tokens / 1_000_000.0) * input_rate + (output_tokens / 1_000_000.0) * output_rate, 6)
    if usd_per_1k_tokens is None:
        usd_per_1k_tokens = 0.01
    total_tokens = input_tokens + output_tokens
    return round((total_tokens / 1000.0) * max(0.0, float(usd_per_1k_tokens)), 6)

def usage_to_dict(
    input_tokens: int,
    output_tokens: int,
    openrouter_usage: Any = None,
    cost_source: str = "openrouter_usage",
) -> Dict[str, float | int | str]:
    """Normalize usage payload with resolved cost and provenance."""
    payload: Dict[str, float | int | str] = {
        "input_tokens": int(input_tokens),
        "output_tokens": int(output_tokens),
        "cost_usd": 0.0,
        "cost_source": "unavailable",
    }

    if openrouter_usage is None:
        return payload

    if isinstance(openrouter_usage, dict):
        read = openrouter_usage.get
    else:
        read = lambda k: getattr(openrouter_usage, k, None)

    raw_cost = read("cost")
    try:
        if raw_cost is not None and float(raw_cost) >= 0:
            reported = round(float(raw_cost), 6)
            payload["openrouter_reported_cost_credits"] = reported
            payload["openrouter_reported_cost_unit"] = "credits"
            payload["cost_usd"] = reported
            payload["cost_source"] = cost_source
    except (TypeError, ValueError):
        pass

    total_tokens = read("total_tokens")
    try:
        if total_tokens is not None:
            payload["total_tokens"] = int(total_tokens)
    except (TypeError, ValueError):
        pass

    completion_details = read("completion_tokens_details")
    if isinstance(completion_details, dict):
        reasoning = completion_details.get("reasoning_tokens")
        try:
            if reasoning is not None:
                payload["reasoning_tokens"] = int(reasoning)
        except (TypeError, ValueError):
            pass

    prompt_details = read("prompt_tokens_details")
    if isinstance(prompt_details, dict):
        for field in ("cached_tokens", "cache_write_tokens", "audio_tokens"):
            try:
                value = prompt_details.get(field)
                if value is not None:
                    payload[field] = int(value)
            except (TypeError, ValueError):
                continue

    cost_details = read("cost_details")
    if isinstance(cost_details, dict):
        upstream = cost_details.get("upstream_inference_cost")
        try:
            if upstream is not None and float(upstream) >= 0:
                payload["upstream_inference_cost_credits"] = round(float(upstream), 6)
        except (TypeError, ValueError):
            pass
    return payload
