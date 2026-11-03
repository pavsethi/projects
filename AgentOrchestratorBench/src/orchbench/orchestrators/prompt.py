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


def build_episode_messages(scenario: Scenario) -> list[dict]:
    """Opening messages for an episode: system + the first scripted user turn."""
    first = scenario.user_turns[0] if scenario.user_turns else ""
    return [
        {"role": "system", "content": MULTITURN_SYSTEM_PROMPT},
        {"role": "user", "content": first},
    ]


def calls_to_text(calls: list[PredictedCall]) -> str:
    """Serialise an assistant turn's tool calls for the message history.

    Shared so every orchestrator formats history identically (parity). This is a
    functional text encoding; mapping to a provider's native tool-call/tool-result
    blocks (for the real Anthropic provider) is an M2 refinement.
    """
    return json.dumps([{"name": c.name, "arguments": c.args} for c in calls])


def results_to_text(results: list[ToolResult]) -> str:
    """Serialise tool results as the next user turn."""
    return json.dumps(
        [{"call": r.call_id, "ok": r.ok, "result": r.content, "error": r.error} for r in results]
    )
