"""BFCL: the Berkeley Function-Calling Leaderboard, as a routing-accuracy suite.

BFCL is the natural fit for "did the orchestrator route to the right tool":
every item is a query plus a set of available functions plus a ground-truth call
(or calls) whose arguments are given as *sets of acceptable values*. That maps
exactly onto :class:`~orchbench.types.GroundTruthCall` and the grader.

Two loaders:

* :func:`load_jsonl` -- our portable one-line-per-task format. The vendored
  sample under ``data/`` uses this; it is what you would hand-author or export.
* :func:`load_bfcl_native` -- reads BFCL's own two-file layout (a ``function``
  file and a ``possible_answer`` file), so you can point the harness at the real
  dataset. See ``METHODOLOGY.md`` for how to fetch it.

BFCL categories map to our ``category`` field: ``simple`` (one call), ``multiple``
(pick one of several offered tools), ``parallel`` (several calls at once).
"""

from __future__ import annotations

import json
from pathlib import Path

from orchbench.types import GroundTruthCall, Task, ToolSpec


def load_jsonl(path: str | Path, suite: str = "bfcl") -> list[Task]:
    """Load tasks from our portable JSONL format (one task object per line)."""
    tasks: list[Task] = []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        obj = json.loads(line)
        tasks.append(
            Task(
                id=obj["id"],
                suite=suite,
                query=obj["query"],
                category=obj.get("category", "simple"),
                tools=[ToolSpec(**t) for t in obj.get("tools", [])],
                ground_truth=[
                    GroundTruthCall(name=g["name"], args=g.get("args", {}))
                    for g in obj.get("ground_truth", [])
                ],
                metadata=obj.get("metadata", {}),
            )
        )
    return tasks


def _native_question_to_query(question: object) -> str:
    """BFCL 'question' is a list of message turns; flatten to the user text."""
    if isinstance(question, str):
        return question
    # Shape: [[{"role": "user", "content": "..."}, ...]]
    if isinstance(question, list):
        turns = question[0] if question and isinstance(question[0], list) else question
        parts = [
            str(turn.get("content", ""))
            for turn in turns
            if isinstance(turn, dict) and turn.get("role") == "user"
        ]
        return "\n".join(p for p in parts if p)
    return str(question)


def load_bfcl_native(
    function_file: str | Path,
    answer_file: str | Path,
    suite: str = "bfcl",
    category: str = "simple",
) -> list[Task]:
    """Load the real BFCL dataset from its native ``function`` + ``answer`` files.

    ``function_file`` lines look like
    ``{"id", "question": [[...]], "function": [ {name, description, parameters} ]}``
    and ``answer_file`` lines like
    ``{"id", "ground_truth": [ {func_name: {param: [values]}} ]}``.
    """
    answers: dict[str, list[dict]] = {}
    for line in Path(answer_file).read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        answers[obj["id"]] = obj["ground_truth"]

    tasks: list[Task] = []
    for line in Path(function_file).read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        ground_truth: list[GroundTruthCall] = []
        for call in answers.get(obj["id"], []):
            # Native shape: {func_name: {param: [acceptable values]}}
            for func_name, args in call.items():
                ground_truth.append(GroundTruthCall(name=func_name, args=args))
        tasks.append(
            Task(
                id=obj["id"],
                suite=suite,
                query=_native_question_to_query(obj.get("question", "")),
                category=obj.get("category", category),
                tools=[
                    ToolSpec(
                        name=f["name"],
                        description=f.get("description", ""),
                        parameters=f.get("parameters", {}),
                    )
                    for f in obj.get("function", [])
                ],
                ground_truth=ground_truth,
            )
        )
    return tasks
