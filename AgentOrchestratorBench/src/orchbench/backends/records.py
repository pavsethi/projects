"""Reference backend: a small stateful record store.

Rich enough to require *ordered, dependent* calls — e.g. "find Alice's order and
mark it shipped" needs search -> (optionally get) -> update, and a wrong id
yields an error the agent must recover from. Deliberately tiny; add richer
backends behind the registry rather than growing this one.

State shape: ``{"records": {record_id: {field: value, ...}}}``.
Goal shape: ``{"field_equals": [{"record": id, "field": f, "value": v}, ...]}``
(every clause must hold on the final state).
"""

from __future__ import annotations

import copy
from typing import Any

from orchbench.types import PredictedCall, ToolResult, ToolSpec

TOOLS: list[ToolSpec] = [
    ToolSpec(
        name="search_records",
        description="Find records whose name contains the query (case-insensitive).",
        parameters={
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    ),
    ToolSpec(
        name="get_record",
        description="Fetch a single record by id.",
        parameters={
            "type": "object",
            "properties": {"record_id": {"type": "string"}},
            "required": ["record_id"],
        },
    ),
    ToolSpec(
        name="update_record",
        description="Set one existing field of a record to a value.",
        parameters={
            "type": "object",
            "properties": {
                "record_id": {"type": "string"},
                "field": {"type": "string"},
                "value": {"type": "string"},
            },
            "required": ["record_id", "field", "value"],
        },
    ),
]


class RecordsBackend:
    """A deterministic record store (see module docstring)."""

    name = "records"

    def __init__(self) -> None:
        self._records: dict[str, dict[str, Any]] = {}

    def reset(self, initial_state: dict) -> None:
        self._records = copy.deepcopy(initial_state.get("records", {}))

    def state(self) -> dict:
        return {"records": copy.deepcopy(self._records)}

    def execute(self, call: PredictedCall) -> ToolResult:
        cid = call.name
        args = call.args or {}
        if call.name == "search_records":
            query = str(args.get("query", "")).lower()
            if "query" not in args:
                return ToolResult(call_id=cid, ok=False, error="missing required arg 'query'")
            hits = [
                {"id": rid, "name": rec.get("name", "")}
                for rid, rec in self._records.items()
                if query in str(rec.get("name", "")).lower()
            ]
            return ToolResult(call_id=cid, ok=True, content=hits)

        if call.name == "get_record":
            rid = args.get("record_id")
            if rid is None:
                return ToolResult(call_id=cid, ok=False, error="missing required arg 'record_id'")
            if rid not in self._records:
                return ToolResult(call_id=cid, ok=False, error=f"no such record: {rid!r}")
            return ToolResult(call_id=cid, ok=True, content=copy.deepcopy(self._records[rid]))

        if call.name == "update_record":
            rid, field, value = args.get("record_id"), args.get("field"), args.get("value")
            if rid is None or field is None or value is None:
                return ToolResult(
                    call_id=cid, ok=False, error="update_record needs record_id, field, value"
                )
            if rid not in self._records:
                return ToolResult(call_id=cid, ok=False, error=f"no such record: {rid!r}")
            if field not in self._records[rid]:
                return ToolResult(
                    call_id=cid, ok=False, error=f"record {rid!r} has no field {field!r}"
                )
            self._records[rid][field] = value
            return ToolResult(call_id=cid, ok=True, content={"updated": rid, field: value})

        return ToolResult(call_id=cid, ok=False, error=f"unknown tool: {call.name!r}")

    def goal_reached(self, goal: dict) -> bool:
        clauses = goal.get("field_equals", [])
        for clause in clauses:
            rec = self._records.get(clause["record"], {})
            if str(rec.get(clause["field"])) != str(clause["value"]):
                return False
        return bool(clauses)


def oracle_plan(scenario: Any) -> list[list[PredictedCall]]:
    """A correct per-turn call plan that solves the scenario.

    Used only by the zero-key mock path (and tests) to drive a *successful*
    episode through the whole pipeline without a real model. For each goal
    clause: search by a word from the record's name, then update the field.
    """
    records = scenario.initial_state.get("records", {})
    plan: list[list[PredictedCall]] = []
    for clause in scenario.goal.get("field_equals", []):
        rid = clause["record"]
        name = str(records.get(rid, {}).get("name", "") or rid)
        query = name.split()[0] if name.split() else rid
        plan.append([PredictedCall(name="search_records", args={"query": query})])
        plan.append(
            [
                PredictedCall(
                    name="update_record",
                    args={"record_id": rid, "field": clause["field"], "value": clause["value"]},
                )
            ]
        )
    return plan
