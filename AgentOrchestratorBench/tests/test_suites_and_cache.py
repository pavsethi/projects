import pathlib

from orchbench.providers.cache import CachingProvider
from orchbench.providers.mock import MockProvider
from orchbench.suites.bfcl import load_bfcl_native, load_jsonl
from orchbench.types import LLMRequest, ModelResponse

SAMPLE = pathlib.Path(__file__).resolve().parents[1] / "data" / "bfcl_sample.jsonl"


def test_sample_loads_and_has_categories():
    tasks = load_jsonl(SAMPLE)
    assert len(tasks) >= 8
    assert {"simple", "multiple", "parallel", "irrelevance"} <= {t.category for t in tasks}
    for t in tasks:
        tool_names = {tool.name for tool in t.tools}
        # Irrelevance tasks intentionally have no ground-truth call.
        if t.category == "irrelevance":
            assert t.ground_truth == []
        else:
            assert t.ground_truth
        # Any ground-truth call must reference a tool the task actually offers.
        for gt in t.ground_truth:
            assert gt.name in tool_names


def test_normalize_json_schema_maps_python_types():
    from orchbench.suites.bfcl import normalize_json_schema

    schema = {
        "type": "dict",
        "properties": {
            "amount": {"type": "float"},
            "tags": {"type": "tuple", "items": {"type": "str"}},
            "count": {"type": "int"},
        },
    }
    out = normalize_json_schema(schema)
    assert out["type"] == "object"
    assert out["properties"]["amount"]["type"] == "number"
    assert out["properties"]["tags"]["type"] == "array"
    assert out["properties"]["tags"]["items"]["type"] == "string"
    assert out["properties"]["count"]["type"] == "integer"


def test_load_bfcl_native_normalizes_types(tmp_path):
    func_file = tmp_path / "f.jsonl"
    ans_file = tmp_path / "a.jsonl"
    func_file.write_text(
        '{"id": "s0", "question": [[{"role": "user", "content": "q"}]], '
        '"function": [{"name": "f", "description": "", '
        '"parameters": {"type": "dict", "properties": {"x": {"type": "float"}}}}]}\n'
    )
    ans_file.write_text('{"id": "s0", "ground_truth": [{"f": {"x": [1.0]}}]}\n')
    tasks = load_bfcl_native(func_file, ans_file)
    params = tasks[0].tools[0].parameters
    assert params["type"] == "object"
    assert params["properties"]["x"]["type"] == "number"


def test_load_bfcl_native_call_string_ground_truth(tmp_path):
    # exec_/live_ categories give ground truth as call strings, not dicts.
    func_file = tmp_path / "f.jsonl"
    ans_file = tmp_path / "a.jsonl"
    func_file.write_text(
        '{"id": "e0", "question": [[{"role": "user", "content": "q"}]], '
        '"function": [{"name": "calc", "description": "", '
        '"parameters": {"type": "dict", "properties": {"n": {"type": "integer"}, '
        '"p": {"type": "float"}}}}]}\n'
    )
    ans_file.write_text('{"id": "e0", "ground_truth": ["calc(n=20, p=0.6)"]}\n')
    tasks = load_bfcl_native(func_file, ans_file)
    gt = tasks[0].ground_truth
    assert len(gt) == 1
    assert gt[0].name == "calc"
    assert gt[0].args == {"n": [20], "p": [0.6]}


def test_load_bfcl_native(tmp_path):
    func_file = tmp_path / "func.jsonl"
    ans_file = tmp_path / "ans.jsonl"
    func_file.write_text(
        '{"id": "simple_0", "question": [[{"role": "user", "content": "weather?"}]], '
        '"function": [{"name": "get_weather", "description": "", '
        '"parameters": {"type": "object", "properties": {"loc": {"type": "string"}}}}]}\n'
    )
    ans_file.write_text('{"id": "simple_0", "ground_truth": [{"get_weather": {"loc": ["SF"]}}]}\n')
    tasks = load_bfcl_native(func_file, ans_file)
    assert len(tasks) == 1
    assert tasks[0].query == "weather?"
    assert tasks[0].tools[0].name == "get_weather"
    assert tasks[0].ground_truth[0].args == {"loc": ["SF"]}


class _CountingProvider:
    name = "counting"

    def __init__(self) -> None:
        self.calls = 0

    async def complete(self, request: LLMRequest) -> ModelResponse:
        self.calls += 1
        return ModelResponse(text="ok", prompt_tokens=10, completion_tokens=2)


async def test_cache_avoids_second_call(tmp_path):
    inner = _CountingProvider()
    cached = CachingProvider(inner, tmp_path / "cache")
    req = LLMRequest(model="m", messages=[{"role": "user", "content": "hi"}])

    first = await cached.complete(req)
    second = await cached.complete(req)

    assert inner.calls == 1  # second served from disk
    assert first.cached is False
    assert second.cached is True


async def test_cache_does_not_store_errors(tmp_path):
    tasks = load_jsonl(SAMPLE)
    # Mock with no fixtures -> error responses, which must not be cached.
    provider = CachingProvider(MockProvider({}), tmp_path / "c2")
    req = LLMRequest(model="m", messages=[], metadata={"task_id": tasks[0].id})
    resp = await provider.complete(req)
    assert resp.error is not None
    assert not any((tmp_path / "c2").iterdir())
