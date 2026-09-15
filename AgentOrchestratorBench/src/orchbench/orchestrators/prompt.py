"""The shared routing prompt.

All orchestrators build the *same* messages from this module so a cross-framework
comparison isolates orchestration overhead, not prompt differences. The first
real run exposed why this matters: the hand-rolled router sent a system prompt
while the framework adapters sent only the user query, so the token/cost spread
reflected prompt construction rather than the frameworks. Centralising the prompt
here enforces prompt parity (see ``METHODOLOGY.md`` -> Fairness caveats).
"""

from __future__ import annotations

from orchbench.types import Task, ToolSpec

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
