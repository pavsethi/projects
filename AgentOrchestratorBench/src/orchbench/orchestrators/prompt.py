"""The shared routing prompt.

All orchestrators build the *same* messages from this module so a cross-framework
comparison isolates orchestration overhead, not prompt differences. The first
real run exposed why this matters: the hand-rolled router sent a system prompt
while the framework adapters sent only the user query, so the token/cost spread
reflected prompt construction rather than the frameworks. Centralising the prompt
here enforces prompt parity (see ``METHODOLOGY.md`` -> Fairness caveats).
"""

from __future__ import annotations

import json

from orchbench.types import PredictedCall, Scenario, Task, ToolResult, ToolSpec

ROUTING_SYSTEM_PROMPT = (
    "You are a tool-routing engine. Given a user request and a set of tools, "
    "call the tool(s) that fulfil the request. If none of the available tools "
    "is appropriate for the request, do not call any tool. When structured "
    "tool-calling is unavailable, reply with a JSON array of objects shaped "
    '{"name": <tool name>, "arguments": {<arg>: <value>}} -- or an empty array '
    "[] if no tool applies -- and nothing else."
)


def tool_to_schema(tool: ToolSpec) -> dict:
    """Render a ToolSpec into the provider-agnostic tool dict shape."""
    return {
        "name": tool.name,
        "description": tool.description,
        "parameters": tool.parameters or {"type": "object", "properties": {}},
    }


def build_routing_messages(task: Task, *, nudge: bool = False) -> list[dict]:
    """The identical system+user messages every orchestrator sends.

    ``nudge`` appends a non-forcing reminder used only on an optional retry; it
    never demands a tool call (which would sabotage the irrelevance category).
    """
    user = task.query
    if nudge:
        user += "\n\n(Reconsider the request and the tools; call a tool only if one applies.)"
    return [
        {"role": "system", "content": ROUTING_SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


# --------------------------------------------------------------------------- #
# Multi-turn (shared by every orchestrator's episode loop — see docs/multi-turn.md).
# --------------------------------------------------------------------------- #

MULTITURN_SYSTEM_PROMPT = (
    "You are a tool-using agent. Fulfil the user's request by calling the "
    "available tools. Tools return results; use each result to decide the next "
    "call, and keep calling until the request is fully done. If a tool returns an "
    "error, adjust and try again. When the task is complete, stop calling tools "
    "and reply with a brief confirmation."
)


def episode_opening(scenario: Scenario) -> list[dict]:
    """Messages before the first user turn: the system prompt, if any.

    ``scenario.system_prompt`` None -> orchbench's default; "" -> none at all
    (BFCL's function-calling mode sends no system prompt).
    """
    prompt = MULTITURN_SYSTEM_PROMPT if scenario.system_prompt is None else scenario.system_prompt
    return [{"role": "system", "content": prompt}] if prompt else []


def user_message(text: str) -> dict:
    return {"role": "user", "content": text}


def assign_call_ids(calls: list[PredictedCall], step_index: int) -> list[PredictedCall]:
    """Give every call an id (providers that don't assign one get a stable one).

    Shared so every orchestrator produces byte-identical history (parity).
    """
    return [
        c if c.id else c.model_copy(update={"id": f"call_{step_index}_{i}"})
        for i, c in enumerate(calls)
    ]


def assistant_message(text: str, calls: list[PredictedCall], native: dict | None) -> dict:
    """One assistant step in provider-agnostic form.

    ``tool_calls`` is the portable view; ``native`` is the provider's raw
    content, which a provider replays verbatim when it recognises it (Anthropic
    requires thinking blocks to be passed back unchanged alongside tool_use).
    """
    msg: dict = {
        "role": "assistant",
        "content": text,
        "tool_calls": [{"id": c.id, "name": c.name, "args": c.args} for c in calls],
    }
    if native:
        msg["native"] = native
    return msg


def result_text(result: ToolResult) -> str:
    """What the model sees for one tool result."""
    if not result.ok:
        return result.error or "Error"
    if isinstance(result.content, str):
        return result.content
    return json.dumps(result.content, ensure_ascii=False)


def tool_results_message(calls: list[PredictedCall], results: list[ToolResult]) -> dict:
    """All results of one step, paired to their calls by id (one message)."""
    return {
        "role": "tool",
        "results": [
            {"id": c.id, "content": result_text(r), "is_error": not r.ok}
            for c, r in zip(calls, results, strict=True)
        ],
    }
