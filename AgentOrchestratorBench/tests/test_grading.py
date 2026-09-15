from orchbench.grading import grade, grade_output
from orchbench.types import (
    FailureMode,
    GroundTruthCall,
    OrchestratorOutput,
    PredictedCall,
    Task,
    ToolSpec,
)


def _task() -> Task:
    return Task(
        id="t",
        suite="bfcl",
        query="weather in SF",
        tools=[ToolSpec(name="get_weather"), ToolSpec(name="get_forecast")],
        ground_truth=[
            GroundTruthCall(
                name="get_weather", args={"location": ["San Francisco"], "unit": ["celsius"]}
            )
        ],
    )


def test_exact_match():
    pred = [
        PredictedCall(name="get_weather", args={"location": "San Francisco", "unit": "celsius"})
    ]
    routing, exact = grade(pred, _task().ground_truth)
    assert routing and exact


def test_routing_correct_but_wrong_args():
    pred = [
        PredictedCall(name="get_weather", args={"location": "San Francisco", "unit": "fahrenheit"})
    ]
    routing, exact = grade(pred, _task().ground_truth)
    assert routing and not exact


def test_wrong_tool():
    pred = [PredictedCall(name="get_forecast", args={"location": "San Francisco"})]
    routing, exact = grade(pred, _task().ground_truth)
    assert not routing and not exact


def test_acceptable_value_set():
    truth = [GroundTruthCall(name="convert", args={"cur": ["USD", "dollars"]})]
    assert grade([PredictedCall(name="convert", args={"cur": "dollars"})], truth) == (True, True)


def test_optional_param_may_be_omitted():
    truth = [GroundTruthCall(name="send", args={"to": ["a@b.com"], "body": ["", ""]})]
    # Omitting the optional body is fine.
    assert grade([PredictedCall(name="send", args={"to": "a@b.com"})], truth) == (True, True)


def test_numeric_string_coercion():
    truth = [GroundTruthCall(name="pct", args={"value": [240]})]
    assert grade([PredictedCall(name="pct", args={"value": "240"})], truth) == (True, True)


def test_parallel_order_independent():
    truth = [
        GroundTruthCall(name="w", args={"loc": ["Tokyo"]}),
        GroundTruthCall(name="w", args={"loc": ["London"]}),
    ]
    pred = [
        PredictedCall(name="w", args={"loc": "London"}),
        PredictedCall(name="w", args={"loc": "Tokyo"}),
    ]
    assert grade(pred, truth) == (True, True)


def test_grade_output_labels_wrong_args():
    out = OrchestratorOutput(
        predicted=[
            PredictedCall(
                name="get_weather", args={"location": "San Francisco", "unit": "fahrenheit"}
            )
        ]
    )
    result = grade_output(_task(), out)
    assert result.routing_correct and not result.exact_correct
    assert result.failure_mode == FailureMode.WRONG_ARGS


def test_grade_output_labels_provider_error():
    out = OrchestratorOutput(predicted=[], error="429 rate limited")
    result = grade_output(_task(), out)
    assert result.failure_mode == FailureMode.PROVIDER_ERROR


def test_grade_output_labels_hallucination():
    out = OrchestratorOutput(predicted=[PredictedCall(name="not_a_tool", args={})])
    result = grade_output(_task(), out)
    assert result.failure_mode == FailureMode.HALLUCINATED_TOOL
