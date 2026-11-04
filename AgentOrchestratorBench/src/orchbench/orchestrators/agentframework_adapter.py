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

from orchbench.backends.base import ToolBackend
from orchbench.episode import StepResult, drive_episode
from orchbench.orchestrators.prompt import build_routing_messages, tool_to_schema
from orchbench.providers.base import LLMProvider
from orchbench.types import (
    LLMRequest,
    ModelResponse,
    OrchestratorOutput,
    PredictedCall,
    Scenario,
    Task,
    Trajectory,
)


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

    async def _call(
        self, provider: LLMProvider, request: LLMRequest
    ) -> tuple[list[PredictedCall], ModelResponse]:
        """One model turn through Agent Framework's chat-client machinery.

        A ``BaseChatClient`` subclass delegates to our shared provider and emits
        the tool calls as ``function_call`` Content; we read them back off the
        ``ChatResponse``. This is the AF-native per-turn path, reused by both the
        single-step router and the episode loop.
        """
        from agent_framework import BaseChatClient, ChatResponse, Content, Message

        holder: dict[str, ModelResponse] = {}

        class _ProviderChatClient(BaseChatClient):
            async def _inner_get_response(
                self, *, messages: Any, stream: bool, options: Any, **kwargs: Any
            ) -> ChatResponse:
                if stream:  # pragma: no cover - the benchmark never streams
                    raise NotImplementedError("streaming is not used by the benchmark")
                model_response = await provider.complete(request)
                holder["response"] = model_response
                contents = [
                    Content(
                        type="function_call", call_id=f"call_{i}", name=c.name, arguments=c.args
                    )
                    for i, c in enumerate(model_response.tool_calls)
                ]
                return ChatResponse(messages=[Message(role="assistant", contents=contents)])

        client = _ProviderChatClient()
        chat = await client.get_response([Message(role="user", contents=["."])])
        return self._extract_calls(chat), holder["response"]

    async def route(self, task: Task, provider: LLMProvider) -> OrchestratorOutput:
        predicted, model_response = await self._call(provider, self._build_request(task))
        if model_response.error is not None:
            return OrchestratorOutput(
                error=model_response.error,
                prompt_tokens=model_response.prompt_tokens,
                completion_tokens=model_response.completion_tokens,
                latency_ms=model_response.latency_ms,
                llm_calls=1,
            )
        return OrchestratorOutput(
            predicted=predicted,
            prompt_tokens=model_response.prompt_tokens,
            completion_tokens=model_response.completion_tokens,
            latency_ms=model_response.latency_ms,
            llm_calls=1,
        )

    async def run_episode(
        self, scenario: Scenario, provider: LLMProvider, backend: ToolBackend
    ) -> Trajectory:
        """Episode via the shared driver, each model turn through AF's chat client.

        AF's own multi-step function-invocation loop builds its requests
        internally, which would bypass our per-turn provider instrumentation (and
        the mock's turn keying); so -- as for the single-step router -- we drive
        the turn loop and let AF own each turn's request/response machinery. This
        keeps the provider seam, backend, and prompt identical across all three.
        """

        async def step(messages: list[dict], tools: list[dict], turn_index: int) -> StepResult:
            request = LLMRequest(
                model=self.model,
                messages=messages,
                tools=tools,
                metadata={"task_id": scenario.id, "turn": turn_index},
            )
            predicted, mr = await self._call(provider, request)
            return StepResult(
                predicted=predicted,
                text=mr.text,
                prompt_tokens=mr.prompt_tokens,
                completion_tokens=mr.completion_tokens,
                latency_ms=mr.latency_ms,
                error=mr.error,
            )

        return await drive_episode(
            scenario,
            backend,
            name=self.name,
            model=self.model,
            provider_name=getattr(provider, "name", "provider"),
            step=step,
            tools=[tool_to_schema(t) for t in scenario.tools],
        )
