"""Unit tests for the Anthropic adapter's pure request-shaping helpers.

The live ``complete()`` call needs the SDK + a key and is out of scope for the
hermetic suite, but the mapping logic -- lifting system turns to the top-level
``system`` param, and the tool-schema shape -- is pure and worth pinning, since
getting it wrong is exactly what produced a real 400/TypeError.
"""

from orchbench.providers.anthropic import AnthropicProvider

to_native = AnthropicProvider._to_anthropic_messages


def test_system_turns_are_lifted():
    messages = [
        {"role": "system", "content": "You are a router."},
        {"role": "user", "content": "weather in SF"},
    ]
    system, convo = to_native(messages)
    assert system == "You are a router."
    # The system turn must not remain in messages (the API rejects it there).
    assert convo == [{"role": "user", "content": [{"type": "text", "text": "weather in SF"}]}]


def test_no_system_turn():
    system, convo = to_native([{"role": "user", "content": "hi"}])
    assert system == ""
    assert convo == [{"role": "user", "content": [{"type": "text", "text": "hi"}]}]


def test_tool_history_maps_to_native_blocks_and_merges_user_turns():
    messages = [
        {"role": "user", "content": "ship it"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [{"id": "call_0_0", "name": "search", "args": {"q": "a"}}],
        },
        {"role": "tool", "results": [{"id": "call_0_0", "content": "[]", "is_error": False}]},
        {"role": "user", "content": "now the next task"},
    ]
    _, convo = to_native(messages)
    assert [m["role"] for m in convo] == ["user", "assistant", "user"]
    assert convo[1]["content"] == [
        {"type": "tool_use", "id": "call_0_0", "name": "search", "input": {"q": "a"}}
    ]
    # Tool results and the next instruction share one user message, results first.
    assert convo[2]["content"] == [
        {"type": "tool_result", "tool_use_id": "call_0_0", "content": "[]"},
        {"type": "text", "text": "now the next task"},
    ]


def test_native_assistant_content_is_replayed_verbatim():
    # Thinking blocks (with signatures) must be passed back unchanged.
    raw = [
        {"type": "thinking", "thinking": "", "signature": "sig"},
        {"type": "tool_use", "id": "toolu_1", "name": "ls", "input": {}},
    ]
    messages = [
        {"role": "user", "content": "list"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [{"id": "toolu_1", "name": "ls", "args": {}}],
            "native": {"provider": "anthropic", "content": raw},
        },
        {"role": "tool", "results": [{"id": "toolu_1", "content": "x", "is_error": True}]},
    ]
    _, convo = to_native(messages)
    assert convo[1]["content"] == raw
    assert convo[2]["content"][0]["is_error"] is True


def test_tools_map_to_input_schema():
    tools = [{"name": "get_weather", "description": "d", "parameters": {"type": "object"}}]
    out = AnthropicProvider._to_anthropic_tools(tools)
    assert out[0]["name"] == "get_weather"
    assert out[0]["input_schema"] == {"type": "object"}
    # A tool with no parameters still gets a valid object schema.
    assert AnthropicProvider._to_anthropic_tools([{"name": "x"}])[0]["input_schema"] == {
        "type": "object",
        "properties": {},
    }
