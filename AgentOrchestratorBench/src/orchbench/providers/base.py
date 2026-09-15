"""The provider seam.

Every provider -- the deterministic :class:`~orchbench.providers.mock.MockProvider`
used in tests and demos, the caching wrapper, and any real backend -- implements
this one async method. Keeping the harness on the *provider* abstraction (rather
than a specific vendor SDK) is what makes it runnable, testable and cacheable
without keys or spend.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from orchbench.types import LLMRequest, ModelResponse


@runtime_checkable
class LLMProvider(Protocol):
    """A minimal async completion interface."""

    #: Human-readable provider name, surfaced in results (e.g. "mock", "anthropic").
    name: str

    async def complete(self, request: LLMRequest) -> ModelResponse:
        """Return a completion for ``request``.

        Implementations must never raise for an *expected* model/provider error;
        instead they return a :class:`ModelResponse` with ``error`` set, so the
        runner can record it as a failure mode rather than crashing the sweep.
        """
        ...
