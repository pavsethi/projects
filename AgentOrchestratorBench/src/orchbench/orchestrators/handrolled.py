"""The hand-rolled orchestrator -- the reference system under test.

This is intentionally *not* a wrapper around a framework: it is the "what does it
actually take to route tool calls yourself" baseline that the framework adapters
are measured against. It does the real work a framework hides -- render tool
schemas into a prompt, call the model, parse a function-calling response,
recover from a malformed one, and account for tokens/latency across retries.

It handles two response shapes so it works against both real function-calling
APIs (structured ``tool_calls``) and models that only emit text (a JSON block we
parse out), which is exactly the portability the harness is meant to reward.
"""

from __future__ import annotations

import json
import re

from orchbench.providers.base import LLMProvider
from orchbench.types import LLMRequest, OrchestratorOutput, PredictedCall, Task, ToolSpec

_SYSTEM_PROMPT = (
    "You are a tool-routing engine. Given a user request and a set of tools, "
    "call the tool(s) that fulfil the request. If none of the available tools "
    "is appropriate for the request, do not call any tool. When structured "
    "tool-calling is unavailable, reply with a JSON array of objects shaped "
    '{"name": <tool name>, "arguments": {<arg>: <value>}} -- or an empty array '
    "[] if no tool applies -- and nothing else."
)

# Matches the first JSON array or object in a block of text (fallback parsing).
_JSON_BLOCK = re.compile(r"(\[.*\]|\{.*\})", re.DOTALL)


def _tool_to_schema(tool: ToolSpec) -> dict:
    return {
        "name": tool.name,
        "description": tool.description,
        "parameters": tool.parameters or {"type": "object", "properties": {}},
    }


def _parse_text_fallback(text: str) -> list[PredictedCall]:
    """Best-effort extraction of tool calls from a plain-text response."""
    match = _JSON_BLOCK.search(text or "")
    if not match:
        return []
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return []
    if isinstance(data, dict):
        data = [data]
    calls: list[PredictedCall] = []
    for item in data:
        if not isinstance(item, dict) or "name" not in item:
            continue
        args = item.get("arguments", item.get("args", {}))
        calls.append(
            PredictedCall(name=str(item["name"]), args=args if isinstance(args, dict) else {})
        )
    return calls


class HandRolledOrchestrator:
    """A minimal, dependency-free tool router with one retry on empty output."""

    def __init__(self, model: str = "mock-model", max_retries: int = 0) -> None:
        # Default 0: one call per task is the honest measurement. A retry that
        # re-prompts an empty response would force a tool call and destroy the
        # irrelevance signal (the model must be free to abstain), so retries are
        # opt-in and the nudge below never demands a call.
        self.name = "handrolled"
        self.model = model
        self.max_retries = max_retries

    def _build_request(self, task: Task, *, nudge: bool = False) -> LLMRequest:
        user = task.query
        if nudge:
            user += "\n\n(Reconsider the request and the tools; call a tool only if one applies.)"
        return LLMRequest(
            model=self.model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user},
            ],
            tools=[_tool_to_schema(t) for t in task.tools],
            metadata={"task_id": task.id},
        )

    async def route(self, task: Task, provider: LLMProvider) -> OrchestratorOutput:
        prompt_tokens = 0
        completion_tokens = 0
        latency_ms = 0.0
        llm_calls = 0
        last_error: str | None = None

        for attempt in range(self.max_retries + 1):
            request = self._build_request(task, nudge=attempt > 0)
            response = await provider.complete(request)

            llm_calls += 1
            prompt_tokens += response.prompt_tokens
            completion_tokens += response.completion_tokens
            latency_ms += response.latency_ms

            if response.error is not None:
                last_error = response.error
                # Provider errors are not fixable by re-prompting; stop.
                break

            predicted = response.tool_calls or _parse_text_fallback(response.text)
            if predicted:
                return OrchestratorOutput(
                    predicted=predicted,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    latency_ms=latency_ms,
                    llm_calls=llm_calls,
                    raw={"attempts": attempt + 1},
                )
            last_error = None  # empty, not an error -- retry may recover it

        return OrchestratorOutput(
            predicted=[],
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            llm_calls=llm_calls,
            error=last_error,
            raw={"attempts": llm_calls},
        )
