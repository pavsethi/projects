"""Load BFCL v4 multi-turn categories as orchbench scenarios.

Faithful to BFCL's function-calling (FC) inference path for Claude:

- **Tools** -- each involved API class's function docs, converted as BFCL's
  ``convert_to_tool`` does for Claude (``dict``->``object``, ``float``->``number``
  with a "This is a float type value." hint, ...), with BFCL's language hint and
  the documented response schema appended to every description. Verified equal
  to upstream's conversion for all 128 multi-turn tools.
- **Turns** -- one scripted user message per BFCL turn. In ``miss_func``, a
  held-out function is withheld from the tool list until its turn, whose (empty)
  user message is replaced with BFCL's "I have updated some more functions"
  prompt.
- **No system prompt** -- BFCL's FC mode sends none.
- **Step limit** -- BFCL force-quits a scenario after more than 20 tool-calling
  steps in one user turn (``MAXIMUM_STEP_LIMIT``).

Data is vendored under ``data/bfcl_multi_turn/`` (Apache-2.0, see its README).
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from orchbench.backends.bfcl import FUNC_DOC_FILES
from orchbench.types import Scenario, ToolSpec

DEFAULT_DIR = Path(__file__).resolve().parents[3] / "data" / "bfcl_multi_turn"

CATEGORIES = ("base", "miss_func", "miss_param", "long_context")

#: BFCL's DEFAULT_USER_PROMPT_FOR_ADDITIONAL_FUNCTION_FC.
ADDITIONAL_FUNCTION_PROMPT = (
    "I have updated some more functions you can choose from. What about now?"
)

#: BFCL's language hint for Python-category function docs.
LANGUAGE_HINT = " Note that the provided function is in Python 3 syntax."

#: BFCL's MAXIMUM_STEP_LIMIT: the scenario is force-quit once a user turn
#: exceeds this many tool-calling steps.
MAXIMUM_STEP_LIMIT = 20

#: BFCL's GORILLA_TO_OPENAPI type mapping (the subset multi-turn docs use, plus
#: the rest of the upstream table for safety).
GORILLA_TO_OPENAPI = {
    "integer": "integer",
    "number": "number",
    "float": "number",
    "string": "string",
    "boolean": "boolean",
    "bool": "boolean",
    "array": "array",
    "list": "array",
    "dict": "object",
    "object": "object",
    "tuple": "array",
    "any": "string",
    "byte": "integer",
    "short": "integer",
    "long": "integer",
    "double": "number",
    "char": "string",
    "ArrayList": "array",
    "Array": "array",
    "HashMap": "object",
}


def _cast_to_openai_type(properties: dict[str, Any]) -> dict[str, Any]:
    """Port of BFCL's ``_cast_to_openai_type`` (same mapping, hints, recursion)."""
    mapping = GORILLA_TO_OPENAPI
    for key, value in properties.items():
        if "type" not in value:
            properties[key]["type"] = "string"
        else:
            var_type = value["type"]
            if var_type == "float":
                properties[key]["format"] = "float"
                properties[key]["description"] += " This is a float type value."
            properties[key]["type"] = mapping.get(var_type, "string")

        prop = properties[key]
        if prop["type"] in ("array", "object"):
            if "properties" in prop:
                prop["properties"] = _cast_to_openai_type(prop["properties"])
            elif "items" in prop:
                items = prop["items"]
                items["type"] = mapping[items["type"]]
                if items["type"] == "array" and "items" in items:
                    items["items"]["type"] = mapping[items["items"]["type"]]
                elif items["type"] == "object" and "properties" in items:
                    items["properties"] = _cast_to_openai_type(items["properties"])
    return properties


def bfcl_tool_spec(doc: dict[str, Any]) -> ToolSpec:
    """One BFCL function doc -> the ToolSpec BFCL would send Claude."""
    doc = copy.deepcopy(doc)
    params = doc.get("parameters") or {"type": "dict", "properties": {}}
    params["type"] = "object"
    params["properties"] = _cast_to_openai_type(params.get("properties", {}))
    description = doc.get("description", "") + LANGUAGE_HINT
    # BFCL folds the documented return schema into the description for Claude
    # (and drops the non-standard ``response`` key).
    if "response" in doc:
        description += (
            f" The response field has the following schema: {json.dumps(doc['response'])}"
        )
    return ToolSpec(name=doc["name"].replace(".", "_"), description=description, parameters=params)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def load_func_docs(cls_name: str, data_dir: Path = DEFAULT_DIR) -> list[dict[str, Any]]:
    return _read_jsonl(data_dir / "multi_turn_func_doc" / FUNC_DOC_FILES[cls_name])


def _user_text(messages: list[dict[str, Any]]) -> str:
    """Combine a turn's consecutive user messages (BFCL's Claude handler does)."""
    return "\n\n".join(str(m["content"]) for m in messages if m.get("role") == "user")


def load_bfcl_multi_turn(
    category: str = "base",
    data_dir: Path = DEFAULT_DIR,
    *,
    limit: int | None = None,
    ids: list[str] | None = None,
) -> list[Scenario]:
    """Load one BFCL multi-turn category as scenarios (optionally a subset)."""
    if category not in CATEGORIES:
        raise ValueError(f"unknown category {category!r}; choose from {CATEGORIES}")
    entries = _read_jsonl(data_dir / f"BFCL_v4_multi_turn_{category}.json")
    answers = {
        a["id"]: a["ground_truth"]
        for a in _read_jsonl(data_dir / "possible_answer" / f"BFCL_v4_multi_turn_{category}.json")
    }
    if ids:
        wanted = set(ids)
        entries = [e for e in entries if e["id"] in wanted]
    if limit is not None:
        entries = entries[:limit]

    doc_cache: dict[str, list[dict[str, Any]]] = {}
    scenarios = []
    for entry in entries:
        classes: list[str] = entry["involved_classes"]
        docs: list[dict[str, Any]] = []
        for cls_name in classes:
            if cls_name not in doc_cache:
                doc_cache[cls_name] = load_func_docs(cls_name, data_dir)
            docs.extend(doc_cache[cls_name])

        # miss_func: withhold functions until their turn (BFCL removes the first
        # doc with that name and re-adds it at the holdout turn).
        missed: dict[str, list[str]] = entry.get("missed_function", {})
        tools_added: dict[int, list[ToolSpec]] = {}
        for turn_key, names in missed.items():
            held = []
            for fname in names:
                idx = next(i for i, d in enumerate(docs) if d["name"] == fname)
                held.append(bfcl_tool_spec(docs.pop(idx)))
            tools_added[int(turn_key)] = held

        user_turns = []
        for t, messages in enumerate(entry["question"]):
            if str(t) in missed:
                user_turns.append(ADDITIONAL_FUNCTION_PROMPT)
            else:
                user_turns.append(_user_text(messages))

        ground_truth = answers[entry["id"]]
        if len(ground_truth) != len(user_turns):
            raise ValueError(f"{entry['id']}: {len(user_turns)} turns, {len(ground_truth)} answers")

        scenarios.append(
            Scenario(
                id=entry["id"],
                suite="bfcl_multi_turn",
                category=category,
                backend="bfcl",
                tools=[bfcl_tool_spec(d) for d in docs],
                tools_added=tools_added,
                user_turns=user_turns,
                initial_state={
                    "initial_config": entry.get("initial_config", {}),
                    "involved_classes": classes,
                    "long_context": category == "long_context",
                    "ground_truth": ground_truth,
                },
                goal={"checker": "bfcl_multi_turn"},
                # Driver aborts when calling steps reach max_turns; BFCL quits
                # once the count exceeds the limit -> limit + 1.
                max_turns=MAXIMUM_STEP_LIMIT + 1,
                system_prompt="",
                metadata={"involved_classes": classes},
            )
        )
    return scenarios
