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

    def __init__(
        self,
        model: str = "claude-sonnet-5",
        api_key: str | None = None,
        thinking: bool = True,
        effort: str | None = None,
        prompt_cache: bool = True,
    ) -> None:
        try:
            from anthropic import AsyncAnthropic
        except ImportError as exc:  # pragma: no cover - exercised only with extra
            raise ImportError(
                "The anthropic extra is required: pip install -e '.[anthropic]'"
            ) from exc

        self.model = model
        # Current Claude models run adaptive thinking by default; thinking=False
        # disables it (cheaper/faster for pure routing). effort tunes depth/spend
        # via output_config; None leaves the server default.
        self.thinking = thinking
        self.effort = effort
        # Top-level automatic prompt caching: each multi-step request re-sends
        # the same tools + growing history, so caching the prefix cuts the bill
        # sharply on long episodes (BFCL's own Claude handler caches too).
        self.prompt_cache = prompt_cache
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
    def _to_anthropic_messages(messages: list[dict]) -> tuple[str, list[dict]]:
        """Map orchbench's provider-agnostic history to Messages API shape.

        - ``system`` turns are lifted to the top-level ``system`` string (a
          ``role: system`` first message is rejected).
        - ``assistant`` turns replay the raw Anthropic content when present
          (thinking blocks must be passed back unchanged with their tool_use
          blocks); otherwise text + ``tool_use`` blocks are built from
          ``tool_calls``.
        - ``tool`` turns become one user message of ``tool_result`` blocks.
        - Consecutive same-role turns are merged (tool results then the next
          user instruction share one user message, results first).
        """
        system_parts: list[str] = []
        out: list[dict] = []

        def push(role: str, blocks: list[dict]) -> None:
            if not blocks:
                return
            if out and out[-1]["role"] == role:
                out[-1]["content"].extend(blocks)
            else:
                out.append({"role": role, "content": list(blocks)})

        for m in messages:
            role = m.get("role")
            if role == "system":
                system_parts.append(str(m["content"]))
            elif role == "user":
                content = m["content"]
                if not isinstance(content, list):
                    content = [{"type": "text", "text": content}]
                push("user", content)
            elif role == "assistant":
                native = m.get("native") or {}
                if native.get("provider") == "anthropic":
                    push("assistant", native["content"])
                    continue
                blocks = [{"type": "text", "text": m["content"]}] if m.get("content") else []
                blocks += [
                    {"type": "tool_use", "id": c["id"], "name": c["name"], "input": c["args"]}
                    for c in m.get("tool_calls", [])
                ]
                push("assistant", blocks)
            elif role == "tool":
                push(
                    "user",
                    [
                        {
                            "type": "tool_result",
                            "tool_use_id": r["id"],
                            "content": r["content"],
                            **({"is_error": True} if r.get("is_error") else {}),
                        }
                        for r in m["results"]
                    ],
                )
        return "\n\n".join(system_parts), out

    async def complete(self, request: LLMRequest) -> ModelResponse:  # pragma: no cover
        start = time.perf_counter()
        system, convo = self._to_anthropic_messages(request.messages)
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
        if not self.thinking:
            kwargs["thinking"] = {"type": "disabled"}
        if self.effort:
            kwargs["output_config"] = {"effort": self.effort}
        if self.prompt_cache:
            kwargs["cache_control"] = {"type": "ephemeral"}
        try:
            message = await self._client.messages.create(**kwargs)
        except Exception as exc:  # noqa: BLE001 - report, never crash the sweep
            return ModelResponse(
                error=f"{type(exc).__name__}: {exc}",
                latency_ms=(time.perf_counter() - start) * 1000,
            )

        latency_ms = (time.perf_counter() - start) * 1000
        tool_calls = [
            PredictedCall(name=block.name, args=dict(block.input), id=block.id)
            for block in message.content
            if getattr(block, "type", None) == "tool_use"
        ]
        text = "".join(
            block.text for block in message.content if getattr(block, "type", None) == "text"
        )
        usage = message.usage
        cache_read = getattr(usage, "cache_read_input_tokens", None) or 0
        cache_write = getattr(usage, "cache_creation_input_tokens", None) or 0
        return ModelResponse(
            tool_calls=tool_calls,
            text=text,
            # prompt_tokens counts the whole prompt; the cache fields say how
            # much of it was billed at cache-read / cache-write rates.
            prompt_tokens=usage.input_tokens + cache_read + cache_write,
            completion_tokens=usage.output_tokens,
            cache_read_tokens=cache_read,
            cache_write_tokens=cache_write,
            latency_ms=latency_ms,
            native={
                "provider": "anthropic",
                "content": [
                    block.model_dump(mode="json", exclude_none=True) for block in message.content
                ],
            },
        )
