"""BFCL multi-turn backend: BFCL's stateful APIs plus a port of its checker.

Executes model tool calls against the vendored BFCL API classes
(``orchbench.vendor.bfcl_multi_turn``) and grades each user turn exactly as
BFCL's ``multi_turn_checker`` does:

1. After every user turn whose ground truth is non-empty, replay that turn's
   ground-truth calls on a separate set of API instances.
2. **Empty-turn check** -- the model must have made at least one call this turn.
3. **State check** -- every public attribute of every API instance must equal
   the ground-truth instance's.
4. **Response check** -- every ground-truth execution result must appear among
   the model's execution results so far (unordered, as a multiset).

The first failing turn fails the scenario. Turns with an empty ground truth
(BFCL's "the model should not / cannot act yet" turns) are not checked, matching
BFCL (its irrelevance checker exists upstream but is never called).

**Safety divergence from upstream:** BFCL builds a Python source string from
each model call and ``eval()``s it, guarded only by a short name denylist. Here
model calls arrive structured (name + JSON args) and are dispatched to a public
method of an involved API instance with ``method(**args)`` -- no code is ever
evaluated. Ground-truth answer strings are parsed with :mod:`ast` (literals
only). The produced result strings match BFCL's formatting exactly.
"""

from __future__ import annotations

import ast
import copy
import importlib
import inspect
import json
from typing import Any

from orchbench.types import PredictedCall, ToolResult

_VENDOR = "orchbench.vendor.bfcl_multi_turn"

#: BFCL API class -> vendored module (BFCL's CLASS_FILE_PATH_MAPPING, multi-turn subset).
CLASS_MODULES: dict[str, str] = {
    "GorillaFileSystem": "gorilla_file_system",
    "MathAPI": "math_api",
    "MessageAPI": "message_api",
    "TwitterAPI": "posting_api",
    "TicketAPI": "ticket_api",
    "TradingBot": "trading_bot",
    "TravelAPI": "travel_booking",
    "VehicleControlAPI": "vehicle_control",
}

#: BFCL API class -> function-doc file (BFCL's MULTI_TURN_FUNC_DOC_FILE_MAPPING).
FUNC_DOC_FILES: dict[str, str] = {
    "GorillaFileSystem": "gorilla_file_system.json",
    "MathAPI": "math_api.json",
    "MessageAPI": "message_api.json",
    "TwitterAPI": "posting_api.json",
    "TicketAPI": "ticket_api.json",
    "TradingBot": "trading_bot.json",
    "TravelAPI": "travel_booking.json",
    "VehicleControlAPI": "vehicle_control.json",
}

#: Classes with no scenario state (BFCL's STATELESS_CLASSES).
STATELESS = {"MathAPI"}

#: Names BFCL refuses to execute (its eval denylist), mirrored for fidelity.
DISALLOWED = {"kill", "exit", "quit", "remove", "unlink", "popen", "Popen", "run"}

_ERROR_PREFIX = "Error during execution: "

#: Long strings in trajectory snapshots are clipped (long_context state is huge).
_SNAPSHOT_STR_LIMIT = 300


def _load_class(name: str) -> type:
    if name not in CLASS_MODULES:
        raise ValueError(f"unknown BFCL API class {name!r}")
    module = importlib.import_module(f"{_VENDOR}.{CLASS_MODULES[name]}")
    cls: type = getattr(module, name)
    return cls


def instantiate(classes: list[str], config: dict, long_context: bool) -> dict[str, Any]:
    """Fresh API instances loaded with a scenario's initial config."""
    instances: dict[str, Any] = {}
    for name in classes:
        inst = _load_class(name)()
        if name not in STATELESS:
            inst._load_scenario(copy.deepcopy(config.get(name, {})), long_context=long_context)
        instances[name] = inst
    return instances


def method_table(instances: dict[str, Any]) -> dict[str, Any]:
    """Public method name -> bound method (later classes win, as in BFCL)."""
    table: dict[str, Any] = {}
    for inst in instances.values():
        for name, method in inspect.getmembers(inst, predicate=inspect.ismethod):
            if not name.startswith("_"):
                table[name] = method
    return table


def format_result(value: Any) -> str:
    """Stringify a return value exactly as BFCL's executor does."""
    if type(value) is str:
        return value
    if type(value) is dict:
        try:
            return json.dumps(value)
        except Exception:  # noqa: BLE001 - mirror upstream's bare fallback
            return str(value)
    return str(value)


def invoke(table: dict[str, Any], name: str, args: tuple, kwargs: dict) -> str:
    """Call one API method; never raises (errors become BFCL's error string)."""
    if name in DISALLOWED:
        return f"{_ERROR_PREFIX}Function call {name} is not allowed."
    method = table.get(name)
    if method is None:
        return f"{_ERROR_PREFIX}name '{name}' is not defined"
    try:
        return format_result(method(*args, **kwargs))
    except Exception as exc:  # noqa: BLE001 - tool errors are results, not crashes
        return f"{_ERROR_PREFIX}{exc}"


def parse_call(source: str) -> tuple[str, tuple, dict]:
    """Parse a ground-truth call string like ``mv(source='a', destination='b')``.

    Literal arguments only (positional allowed); never evaluates code.
    """
    node = ast.parse(source.strip(), mode="eval").body
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
        raise ValueError(f"not a simple call: {source!r}")
    args = tuple(ast.literal_eval(a) for a in node.args)
    kwargs = {kw.arg: ast.literal_eval(kw.value) for kw in node.keywords if kw.arg}
    return node.func.id, args, kwargs


def _looks_failed(text: str) -> bool:
    """For metrics only: an exception, or an API-level ``{"error": ...}`` result."""
    if text.startswith(_ERROR_PREFIX):
        return True
    if text.startswith("{"):
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return False
        return isinstance(payload, dict) and "error" in payload
    return False


def _public_state(inst: Any) -> dict[str, Any]:
    return {k: v for k, v in vars(inst).items() if not k.startswith("_")}


def _jsonable(value: Any, depth: int = 0) -> Any:
    """A JSON-safe, size-bounded view of API state (for trajectories only)."""
    if depth > 12:
        return "..."
    if isinstance(value, str):
        if len(value) > _SNAPSHOT_STR_LIMIT:
            return value[:_SNAPSHOT_STR_LIMIT] + f"... (+{len(value) - _SNAPSHOT_STR_LIMIT} chars)"
        return value
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, dict):
        return {str(k): _jsonable(v, depth + 1) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v, depth + 1) for v in value]
    if hasattr(value, "__dict__"):
        return {k: _jsonable(v, depth + 1) for k, v in _public_state(value).items()}
    return str(value)


def _compare(model_inst: Any, gt_inst: Any) -> dict[str, Any]:
    """Public attributes that differ (BFCL's ``_compare_instances``)."""
    diffs: dict[str, Any] = {}
    for attr in vars(gt_inst):
        if attr.startswith("_"):
            continue
        m, g = getattr(model_inst, attr), getattr(gt_inst, attr)
        if m != g:
            diffs[attr] = {"model": _jsonable(m), "ground_truth": _jsonable(g)}
    return diffs


def _missing_unordered(expected: list[str], actual: list[str]) -> list[str]:
    """Items of ``expected`` not covered by ``actual`` (multiset), as in BFCL."""
    pool = list(actual)
    missing = []
    for item in expected:
        try:
            pool.remove(item)
        except ValueError:
            missing.append(item)
    return missing


class BFCLBackend:
    """BFCL multi-turn world + per-user-turn checker.

    ``initial_state`` carries everything the checker needs (BFCL grades after
    each user turn, so the ground truth must be known up front)::

        {"initial_config": {...}, "involved_classes": [...],
         "long_context": bool, "ground_truth": [[call, ...], ...]}
    """

    name = "bfcl"

    def __init__(self) -> None:
        self._ground_truth: list[list[str]] = []
        self._model: dict[str, Any] = {}
        self._gt: dict[str, Any] = {}
        self._model_table: dict[str, Any] = {}
        self._gt_table: dict[str, Any] = {}
        self._turn_calls = 0
        self._all_model_results: list[str] = []
        self._checked = 0
        self._failure: dict[str, Any] | None = None
        self._complete = False

    def reset(self, initial_state: dict) -> None:
        classes = initial_state["involved_classes"]
        config = initial_state.get("initial_config", {})
        long_context = bool(initial_state.get("long_context", False))
        self._ground_truth = initial_state["ground_truth"]
        self._model = instantiate(classes, config, long_context)
        self._gt = instantiate(classes, config, long_context)
        self._model_table = method_table(self._model)
        self._gt_table = method_table(self._gt)
        self._turn_calls = 0
        self._all_model_results = []
        self._checked = 0
        self._failure = None
        self._complete = False

    def execute(self, call: PredictedCall) -> ToolResult:
        text = invoke(self._model_table, call.name, (), dict(call.args))
        self._turn_calls += 1
        self._all_model_results.append(text)
        failed = _looks_failed(text)
        return ToolResult(
            call_id=call.id or call.name,
            ok=not failed,
            content=text,
            error=text if failed else None,
            is_error=False,  # BFCL never flags tool errors to the model
        )

    def end_user_turn(self, turn: int) -> None:
        made_calls, self._turn_calls = self._turn_calls > 0, 0
        if self._failure is None and turn < len(self._ground_truth):
            self._check_turn(turn, made_calls)
        self._checked = turn + 1
        if turn >= len(self._ground_truth) - 1:
            self._complete = True

    def _check_turn(self, turn: int, made_calls: bool) -> None:
        gt_calls = self._ground_truth[turn]
        gt_results = [invoke(self._gt_table, *parse_call(c)) for c in gt_calls]
        if not gt_calls:
            return  # nothing required this turn (BFCL skips the checks)
        if not made_calls:
            self._fail(turn, "empty_turn", "Model made no call on a turn that requires calls.")
            return
        for cls_name, gt_inst in self._gt.items():
            diffs = _compare(self._model[cls_name], gt_inst)
            if diffs:
                self._fail(
                    turn,
                    "state_mismatch",
                    f"{cls_name} state differs from ground truth.",
                    differences=diffs,
                )
                return
        missing = _missing_unordered(gt_results, self._all_model_results)
        if missing:
            self._fail(
                turn,
                "response_mismatch",
                "Some ground-truth results were never produced by the model's calls.",
                missing=[_jsonable(m) for m in missing],
            )

    def _fail(self, turn: int, kind: str, message: str, **details: Any) -> None:
        self._failure = {
            "failed_user_turn": turn,
            "error_type": kind,
            "failure_mode": kind,
            "message": message,
            "expected_calls": self._ground_truth[turn],
            **details,
        }

    def state(self) -> dict:
        return {
            name: _jsonable(_public_state(inst))
            for name, inst in self._model.items()
            if name not in STATELESS
        }

    def goal_reached(self, goal: dict) -> bool:
        return self._complete and self._failure is None

    def grade_detail(self) -> dict:
        n = len(self._ground_truth)
        if self._failure is not None:
            return {"n_user_turns": n, **self._failure}
        if not self._complete:
            # Aborted (step cap or provider error) before every turn was checked.
            return {
                "n_user_turns": n,
                "checked_user_turns": self._checked,
                "error_type": "incomplete",
            }
        return {"n_user_turns": n, "checked_user_turns": n}


def oracle_plan(scenario: Any) -> list[list[PredictedCall]]:
    """Replay the ground truth as model steps (zero-key mock path and tests).

    Per user turn: one step with all of that turn's ground-truth calls, then an
    empty step to end the turn; an empty-ground-truth turn is a single empty
    step. Positional ground-truth arguments are bound to parameter names via the
    API method's signature, since tool calls are always keyword-only.
    """
    state = scenario.initial_state
    owners: dict[str, type] = {}
    for name in state["involved_classes"]:
        cls = _load_class(name)
        for meth, _ in inspect.getmembers(cls, predicate=inspect.isfunction):
            if not meth.startswith("_"):
                owners[meth] = cls

    plan: list[list[PredictedCall]] = []
    for turn in state["ground_truth"]:
        calls = []
        for source in turn:
            fname, args, kwargs = parse_call(source)
            if args and fname in owners:
                bound = inspect.signature(getattr(owners[fname], fname)).bind(None, *args, **kwargs)
                kwargs = {k: v for k, v in bound.arguments.items() if k != "self"}
            calls.append(PredictedCall(name=fname, args=kwargs))
        plan.extend([calls, []] if calls else [[]])
    return plan
