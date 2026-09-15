"""Microsoft Agent Framework adapter (import-guarded).

Install with ``pip install -e '.[agentframework]'``.

Microsoft Agent Framework is the unified successor to Semantic Kernel and
AutoGen. Like the LangGraph adapter, this drives the framework over the
harness's *shared* provider seam rather than letting it call its own model
backend, so what's compared is the framework's request/response machinery
(``ChatOptions`` normalisation, ``ChatResponse``/``Content`` round-trip, the
``get_response`` client contract) -- not a different LLM.

Mechanism: we subclass ``agent_framework.BaseChatClient`` and override its one
abstract method, ``_inner_get_response``, to call our ``LLMProvider`` and return
a ``ChatResponse`` whose assistant message carries the tool calls as
``function_call`` ``Content`` blocks. We then read those blocks back off the
response -- the single routing turn, the correct unit for routing accuracy
(matching the LangGraph adapter).
"""

from __future__ import annotations

import json
from typing import Any

from orchbench.orchestrators.prompt import build_routing_messages, tool_to_schema
from orchbench.providers.base import LLMProvider
from orchbench.types import LLMRequest, OrchestratorOutput, PredictedCall, Task


def _require_agent_framework() -> None:
    try:
        import agent_framework  # noqa: F401
    except ImportError as exc:  # pragma: no cover - exercised only with extra
        raise ImportError(
            "The agentframework extra is required: pip install -e '.[agentframework]'"
        ) from exc


class AgentFrameworkOrchestrator:
    """Route tasks through Microsoft Agent Framework over the shared provider."""

    def __init__(self, model: str = "mock-model") -> None:
        _require_agent_framework()
        self.name = "agentframework"
        self.model = model

    def _build_request(self, task: Task) -> LLMRequest:
        # Identical prompt to every other orchestrator (prompt parity).
        return LLMRequest(
            model=self.model,
            messages=build_routing_messages(task),
            tools=[tool_to_schema(t) for t in task.tools],
            metadata={"task_id": task.id},
        )

    @staticmethod
    def _extract_calls(response: Any) -> list[PredictedCall]:
        """Pull ``function_call`` Content blocks out of a ChatResponse.

        Isolated because content shapes are the part most likely to shift across
        SDK versions. ``arguments`` may arrive as a dict or a JSON string.
        """
        calls: list[PredictedCall] = []
        for message in getattr(response, "messages", []) or []:
            for content in getattr(message, "contents", []) or []:
                if getattr(content, "type", None) != "function_call":
                    continue
                args = content.arguments
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}
                calls.append(
                    PredictedCall(name=content.name, args=args if isinstance(args, dict) else {})
                )
        return calls

    async def route(self, task: Task, provider: LLMProvider) -> OrchestratorOutput:
        from agent_framework import BaseChatClient, ChatResponse, Content, Message

        request = self._build_request(task)
        # The client stashes our raw ModelResponse here so route() can read the
        # token/latency/error accounting the framework's types don't carry.
        holder: dict[str, Any] = {}

        class _ProviderChatClient(BaseChatClient):
            async def _inner_get_response(
                self,
                *,
                messages: Any,
                stream: bool,
                options: Any,
                **kwargs: Any,
            ) -> ChatResponse:
                if stream:  # pragma: no cover - the benchmark never streams
                    raise NotImplementedError("streaming is not used by the routing benchmark")
                model_response = await provider.complete(request)
                holder["response"] = model_response
                contents = [
                    Content(
                        type="function_call",
                        call_id=f"call_{i}",
                        name=call.name,
                        arguments=call.args,
                    )
                    for i, call in enumerate(model_response.tool_calls)
                ]
                return ChatResponse(messages=[Message(role="assistant", contents=contents)])

        client = _ProviderChatClient()
        chat = await client.get_response([Message(role="user", contents=[task.query])])
        model_response = holder["response"]

        if model_response.error is not None:
            return OrchestratorOutput(
                error=model_response.error,
                prompt_tokens=model_response.prompt_tokens,
                completion_tokens=model_response.completion_tokens,
                latency_ms=model_response.latency_ms,
                llm_calls=1,
            )
        return OrchestratorOutput(
            predicted=self._extract_calls(chat),
            prompt_tokens=model_response.prompt_tokens,
            completion_tokens=model_response.completion_tokens,
            latency_ms=model_response.latency_ms,
            llm_calls=1,
        )
