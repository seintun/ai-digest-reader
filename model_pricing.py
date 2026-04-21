"""Model pricing helpers for run-cost accounting."""
from __future__ import annotations

from typing import Dict

# Static configured rate (user-provided): Moonshot AI
# Input: $0.213 / 1M tokens, Output: $4.00 / 1M tokens
KIMI_K2_6_INPUT_PER_M = 0.213
KIMI_K2_6_OUTPUT_PER_M = 4.00


def compute_kimi_k26_cost_usd(input_tokens: int, output_tokens: int) -> float:
    """Compute USD cost for Kimi K2.6 tokens."""
    in_cost = (max(0, int(input_tokens)) / 1_000_000) * KIMI_K2_6_INPUT_PER_M
    out_cost = (max(0, int(output_tokens)) / 1_000_000) * KIMI_K2_6_OUTPUT_PER_M
    return round(in_cost + out_cost, 6)


def usage_to_dict(input_tokens: int, output_tokens: int) -> Dict[str, float | int]:
    """Normalize usage payload with computed cost."""
    return {
        "input_tokens": int(input_tokens),
        "output_tokens": int(output_tokens),
        "cost_usd": compute_kimi_k26_cost_usd(input_tokens, output_tokens),
    }
