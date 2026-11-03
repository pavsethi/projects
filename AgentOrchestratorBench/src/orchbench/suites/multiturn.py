"""Loader for multi-turn scenarios (portable JSONL).

Same spirit as the BFCL loader: one scenario object per line. If a scenario
omits ``tools``, they're filled from the backend's default tool set so sample
files stay terse.
"""

from __future__ import annotations

import json
from pathlib import Path

from orchbench.backends import default_tools
from orchbench.types import Scenario, ToolSpec


def load_scenarios(path: str | Path) -> list[Scenario]:
    scenarios: list[Scenario] = []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        obj = json.loads(line)
        tools = [ToolSpec(**t) for t in obj.get("tools", [])]
        if not tools:
            tools = default_tools(obj.get("backend", "records"))
        scenarios.append(
            Scenario(
                id=obj["id"],
                suite=obj.get("suite", "multiturn"),
                category=obj.get("category", "multi_turn"),
                tools=tools,
                user_turns=obj.get("user_turns", []),
                backend=obj.get("backend", "records"),
                initial_state=obj.get("initial_state", {}),
                goal=obj.get("goal", {}),
                max_turns=obj.get("max_turns", 8),
                metadata=obj.get("metadata", {}),
            )
        )
    return scenarios
