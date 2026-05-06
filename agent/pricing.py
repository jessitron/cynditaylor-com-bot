"""Marginal AWS prices used to stamp cost.* attrs on spans.

Quantities and prices are stamped separately so the bill stays auditable and
prices can be refreshed by editing one constant — no rewrite of historical
telemetry. All values are post-free-tier marginal rates.
"""

from __future__ import annotations

_PER_MTOK = 1_000_000


def _per_token(price_per_mtok: float) -> float:
    return price_per_mtok / _PER_MTOK


# https://aws.amazon.com/ses/pricing/ — outbound. Inbound (receipt + chunks)
# is the dispatcher's responsibility; see lambda/invoke_agent.
SES_SEND_USD = 0.0001

# https://aws.amazon.com/bedrock/agentcore/pricing/ — AgentCore Runtime.
AGENTCORE_CPU_USD_PER_HOUR = 0.0895
AGENTCORE_MEMORY_USD_PER_GB_HOUR = 0.00945


# Bedrock token pricing — anchor for the Bedrock cost stamper.
# Source: https://aws.amazon.com/bedrock/pricing/ (Anthropic on-demand list
# prices). Cache prices assume the 5-minute TTL, which is the Bedrock default.


# Keyed by Bedrock inference-profile model id (the value of gen_ai.request.model).
PRICES: dict[str, dict[str, float]] = {
    "us.anthropic.claude-sonnet-4-5-20250929-v1:0": {
        "input": _per_token(3.00),
        "output": _per_token(15.00),
        "cache_read": _per_token(0.30),
        "cache_write": _per_token(3.75),
    },
    "us.anthropic.claude-opus-4-7": {
        "input": _per_token(15.00),
        "output": _per_token(75.00),
        "cache_read": _per_token(1.50),
        "cache_write": _per_token(18.75),
    },
}


def lookup(model_id: str | None) -> dict[str, float] | None:
    if not model_id:
        return None
    return PRICES.get(model_id)
