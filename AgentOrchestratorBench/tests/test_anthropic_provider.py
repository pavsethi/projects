"""Unit tests for the Anthropic adapter's pure request-shaping helpers.

The live ``complete()`` call needs the SDK + a key and is out of scope for the
hermetic suite, but the mapping logic -- lifting system turns to the top-level
``system`` param, and the tool-schema shape -- is pure and worth pinning, since
getting it wrong is exactly what produced a real 400/TypeError.
"""

from orchbench.providers.anthropic import AnthropicProvider


def test_split_system_lifts_system_turns():
    messages = [
        {"role": "system", "content": "You are a router."},
        {"role": "user", "content": "weather in SF"},
    ]
    system, convo = AnthropicProvider._split_system(messages)
    assert system == "You are a router."
    # The system turn must not remain in messages (the API rejects it there).
    assert convo == [{"role": "user", "content": "weather in SF"}]


def test_split_system_with_no_system_turn():
    messages = [{"role": "user", "content": "hi"}]
    system, convo = AnthropicProvider._split_system(messages)
    assert system == ""
    assert convo == messages


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
