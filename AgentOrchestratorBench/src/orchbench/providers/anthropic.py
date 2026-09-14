"""Optional real provider backed by the Anthropic Messages API.

Import-guarded: the core harness installs and tests without the ``anthropic``
SDK. Install with ``pip install -e '.[anthropic]'`` and set ``ANTHROPIC_API_KEY``.

This is the reference implementation of a *real* provider -- it shows exactly
how the mock's contract maps onto a production function-calling API (tool
schema shape, ``tool_use`` block parsing, token accounting, error capture).
"""

from __future__ import annotations

import os
import time

from orchbench.types import LLMRequest, ModelResponse, PredictedCall


class AnthropicProvider:
    """Adapter over ``anthropic.AsyncAnthropic``."""

    name = "anthropic"

    def __init__(self, model: str = "claude-sonnet-5", api_key: str | None = None) -> None:
        try:
            from anthropic import AsyncAnthropic
        except ImportError as exc:  # pragma: no cover - exercised only with extra
            raise ImportError(
                "The anthropic extra is required: pip install -e '.[anthropic]'"
            ) from exc

        self.model = model
        self._client = AsyncAnthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

    @staticmethod
    def _to_anthropic_tools(tools: list[dict]) -> list[dict]:
        """Map our ToolSpec-shaped dicts to Anthropic's tool schema."""
        out = []
        for tool in tools:
            out.append(
                {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "input_schema": tool.get("parameters") or {"type": "object", "properties": {}},
                }
            )
        return out

    @staticmethod
    def _split_system(messages: list[dict]) -> tuple[str, list[dict]]:
        """Lift ``role: system`` turns into the top-level ``system`` string.

        Our internal message format lets orchestrators put a system prompt in the
        messages list, but the Messages API takes ``system`` as a top-level
        parameter (a leading ``role: system`` message is rejected). Concatenate
        any system turns and pass the rest through unchanged.
        """
        system_parts = [str(m["content"]) for m in messages if m.get("role") == "system"]
        convo = [m for m in messages if m.get("role") != "system"]
        return "\n\n".join(system_parts), convo

    async def complete(self, request: LLMRequest) -> ModelResponse:  # pragma: no cover
        start = time.perf_counter()
        system, convo = self._split_system(request.messages)
        # Note: sampling params (temperature/top_p/top_k) were removed on the
        # Claude 5-family models and the current SDK drops `temperature` from
        # messages.create() entirely -- so it is intentionally not passed.
        kwargs: dict = {
            "model": self.model,
            "max_tokens": request.max_tokens,
            "tools": self._to_anthropic_tools(request.tools),
            "messages": convo,
        }
        if system:
            kwargs["system"] = system
        try:
            message = await self._client.messages.create(**kwargs)
        except Exception as exc:  # noqa: BLE001 - report, never crash the sweep
            return ModelResponse(
                error=f"{type(exc).__name__}: {exc}",
                latency_ms=(time.perf_counter() - start) * 1000,
            )

        latency_ms = (time.perf_counter() - start) * 1000
        tool_calls = [
            PredictedCall(name=block.name, args=dict(block.input))
            for block in message.content
            if getattr(block, "type", None) == "tool_use"
        ]
        text = "".join(
            block.text for block in message.content if getattr(block, "type", None) == "text"
        )
        return ModelResponse(
            tool_calls=tool_calls,
            text=text,
            prompt_tokens=message.usage.input_tokens,
            completion_tokens=message.usage.output_tokens,
            latency_ms=latency_ms,
        )
