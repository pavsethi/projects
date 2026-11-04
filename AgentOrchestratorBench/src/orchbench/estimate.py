"""Pre-flight cost estimate for a real multi-turn run (no API calls).

Replays each scenario's oracle plan through the real driver with a recording
provider, sizes every request the way the Anthropic provider would send it
(tools + native message blocks), and prices it at list price, with and without
prompt caching. Real models take more steps than the oracle (sequential calls,
exploration, retries), so the result is a *range*: oracle-length as the low end,
``STEP_MULTIPLIER``x as the high end. Token counts are approximated from JSON
size, so treat the numbers as +/-50%.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass

from orchbench.backends import get_backend, oracle_plan
from orchbench.metrics import CACHE_READ_MULT, CACHE_WRITE_MULT, PRICING
from orchbench.orchestrators.handrolled import HandRolledOrchestrator
from orchbench.providers.anthropic import AnthropicProvider
from orchbench.providers.mock import MockProvider, build_episode_fixtures
from orchbench.types import LLMRequest, ModelResponse, Scenario

CHARS_PER_TOKEN = 3.5  # JSON-heavy prompts tokenize densely; errs high
OUTPUT_TOKENS_PER_STEP = 250  # tool call + brief thinking at low effort
STEP_MULTIPLIER = 2.5  # high end: real runs take more steps than the oracle


@dataclass
class Estimate:
    scenarios: int
    orchestrators: int
    oracle_steps: int
    input_tokens: int  # oracle-length, all orchestrators
    low_usd: float  # oracle-length, prompt caching on
    high_usd: float  # STEP_MULTIPLIER x, prompt caching on
    high_usd_no_cache: float  # STEP_MULTIPLIER x, no caching


class _Sizer:
    """A mock provider wrapper that records the size of every request."""

    name = "sizer"

    def __init__(self, inner: MockProvider) -> None:
        self.inner = inner
        self.sizes: list[int] = []

    async def complete(self, request: LLMRequest) -> ModelResponse:
        system, messages = AnthropicProvider._to_anthropic_messages(request.messages)
        payload = {
            "system": system,
            "tools": AnthropicProvider._to_anthropic_tools(request.tools),
            "messages": messages,
        }
        self.sizes.append(int(len(json.dumps(payload)) / CHARS_PER_TOKEN))
        return await self.inner.complete(request)


async def _episode_sizes(scenario: Scenario) -> list[int]:
    sizer = _Sizer(MockProvider(build_episode_fixtures(scenario.id, oracle_plan(scenario))))
    await HandRolledOrchestrator().run_episode(scenario, sizer, get_backend(scenario.backend))
    return sizer.sizes


def _cost(sizes: list[int], in_price: float, out_price: float, cache: bool) -> float:
    total = 0.0
    prev = 0
    for size in sizes:
        if cache:
            # The previous request is a cached prefix; the new tail is written.
            read, write = min(prev, size), max(size - prev, 0)
            total += (read * CACHE_READ_MULT + write * CACHE_WRITE_MULT) * in_price
        else:
            total += size * in_price
        total += OUTPUT_TOKENS_PER_STEP * out_price
        prev = size
    return total / 1_000_000


def _stretch(sizes: list[int], factor: float) -> list[int]:
    """A longer episode: more steps, each request growing at the same rate."""
    if not sizes:
        return sizes
    n = max(len(sizes), round(len(sizes) * factor))
    growth = (sizes[-1] - sizes[0]) / max(len(sizes) - 1, 1)
    return [int(sizes[0] + growth * i) for i in range(n)]


def estimate_run(scenarios: list[Scenario], model: str, n_orchestrators: int) -> Estimate:
    in_price, out_price = PRICING.get(model, (0.0, 0.0))

    async def gather() -> list[list[int]]:
        return [await _episode_sizes(s) for s in scenarios]

    all_sizes = asyncio.run(gather())
    low = sum(_cost(sz, in_price, out_price, True) for sz in all_sizes)
    stretched = [_stretch(sz, STEP_MULTIPLIER) for sz in all_sizes]
    high = sum(_cost(sz, in_price, out_price, True) for sz in stretched)
    high_nc = sum(_cost(sz, in_price, out_price, False) for sz in stretched)
    return Estimate(
        scenarios=len(scenarios),
        orchestrators=n_orchestrators,
        oracle_steps=sum(len(sz) for sz in all_sizes) * n_orchestrators,
        input_tokens=sum(sum(sz) for sz in all_sizes) * n_orchestrators,
        low_usd=low * n_orchestrators,
        high_usd=high * n_orchestrators,
        high_usd_no_cache=high_nc * n_orchestrators,
    )
