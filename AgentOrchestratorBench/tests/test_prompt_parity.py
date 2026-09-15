"""Prompt parity: every orchestrator must send the *same* prompt.

The first real run exposed a confounder -- the hand-rolled router sent a system
prompt while the framework adapters sent only the user query, so the token/cost
spread reflected prompt construction, not the frameworks. These tests pin parity
so that regression can't slip back in.
"""

import pathlib

import pytest

from orchbench.orchestrators.handrolled import HandRolledOrchestrator
from orchbench.orchestrators.prompt import ROUTING_SYSTEM_PROMPT, build_routing_messages
from orchbench.suites.bfcl import load_jsonl

SAMPLE = pathlib.Path(__file__).resolve().parents[1] / "data" / "bfcl_sample.jsonl"


def test_build_routing_messages_shape():
    task = load_jsonl(SAMPLE)[0]
    msgs = build_routing_messages(task)
    assert [m["role"] for m in msgs] == ["system", "user"]
    assert msgs[0]["content"] == ROUTING_SYSTEM_PROMPT
    assert task.query in msgs[1]["content"]


def test_nudge_never_forces_a_call():
    task = load_jsonl(SAMPLE)[0]
    nudged = build_routing_messages(task, nudge=True)[1]["content"]
    # The retry nudge must not demand a tool call (that would break irrelevance).
    assert "only if one applies" in nudged
    assert "must call" not in nudged.lower()


def test_all_orchestrators_send_identical_prompt():
    """Hand-rolled + both framework adapters must build the same request."""
    lg = pytest.importorskip("orchbench.orchestrators.langgraph_adapter")
    af = pytest.importorskip("orchbench.orchestrators.agentframework_adapter")
    pytest.importorskip("langgraph")
    pytest.importorskip("agent_framework")

    task = load_jsonl(SAMPLE)[0]
    h = HandRolledOrchestrator(model="m")._build_request(task)
    lg_req = lg.LangGraphOrchestrator(model="m")._build_request(task)
    af_req = af.AgentFrameworkOrchestrator(model="m")._build_request(task)

    assert h.messages == lg_req.messages == af_req.messages
    assert h.tools == lg_req.tools == af_req.tools
