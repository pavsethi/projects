"""Retry-with-backoff wrapper for any provider.

A sweep of hundreds of live calls will hit transient 429s and 5xx. Providers
report those as a :class:`~orchbench.types.ModelResponse` with ``error`` set
(they never raise), so this wrapper inspects the error and re-issues the request
with exponential backoff + jitter. Non-transient errors (a 400 bad request, an
auth failure) are returned immediately -- retrying them just wastes money.

Compose it around the real provider, inside the cache, e.g.::

    provider = CachingProvider(RetryProvider(AnthropicProvider(...)), ".cache")

so successful responses are cached and only genuine transients are retried.
"""

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable

from orchbench.providers.base import LLMProvider
from orchbench.types import LLMRequest, ModelResponse

# Substrings that mark an error worth retrying. Matched case-insensitively.
_TRANSIENT_MARKERS = (
    "429",
    "rate limit",
    "overloaded",
    "timeout",
    "timed out",
    "500",
    "502",
    "503",
    "504",
    "connection",
    "temporarily",
)


def is_transient(error: str) -> bool:
    low = error.lower()
    return any(marker in low for marker in _TRANSIENT_MARKERS)


class RetryProvider:
    """Retry a wrapped provider on transient errors with exponential backoff."""

    def __init__(
        self,
        inner: LLMProvider,
        max_retries: int = 3,
        base_delay: float = 0.5,
        max_delay: float = 8.0,
        sleep: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        self._inner = inner
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self._sleep = sleep or asyncio.sleep
        self.name = getattr(inner, "name", "provider")

    def _backoff(self, attempt: int) -> float:
        # Exponential with full jitter: random in [0, min(max, base * 2**attempt)].
        ceiling = min(self.max_delay, self.base_delay * (2**attempt))
        return random.uniform(0, ceiling)

    async def complete(self, request: LLMRequest) -> ModelResponse:
        response = await self._inner.complete(request)
        attempt = 0
        while (
            response.error is not None
            and is_transient(response.error)
            and attempt < self.max_retries
        ):
            await self._sleep(self._backoff(attempt))
            attempt += 1
            response = await self._inner.complete(request)
        return response
