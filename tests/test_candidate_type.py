# Copyright (c) 2025 Lakshya A Agrawal and the GEPA contributors
# https://github.com/gepa-ai/gepa

"""Tests for CandidateT defaulting to str.

Verifies that GEPAAdapter, ProposalFn, and related types correctly
use dict[str, CandidateT] where CandidateT defaults to str.
"""

from collections.abc import Mapping, Sequence
from typing import Any

from gepa.core.adapter import CandidateT, EvaluationBatch, ProposalFn

# ---------------------------------------------------------------------------
# Concrete adapter typed with string component values
# ---------------------------------------------------------------------------


class TypedAdapter:
    """Concrete GEPAAdapter implementation with dict[str, str] candidates."""

    def evaluate(
        self,
        batch: list[str],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> EvaluationBatch[str, str]:
        has_text = all(isinstance(component, str) and component for component in candidate.values())
        scores = [1.0 if has_text else 0.0 for _ in batch]
        outputs = [f"output_{i}" for i in range(len(batch))]
        trajectories = [f"trace_{i}" for i in range(len(batch))] if capture_traces else None
        return EvaluationBatch(outputs=outputs, scores=scores, trajectories=trajectories)

    def make_reflective_dataset(
        self,
        candidate: dict[str, str],
        eval_batch: EvaluationBatch[str, str],
        components_to_update: list[str],
    ) -> Mapping[str, Sequence[Mapping[str, Any]]]:
        dataset: dict[str, list[dict[str, Any]]] = {}
        for name in components_to_update:
            component = candidate.get(name)
            if component is None:
                continue
            dataset[name] = [
                {
                    "Inputs": {"component_text": component},
                    "Generated Outputs": str(eval_batch.outputs),
                    "Feedback": "Example feedback for testing",
                }
            ]
        return dataset

    propose_improvements: ProposalFn | None = None


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_typed_adapter_evaluate_returns_correct_shape():
    """evaluate() with dict[str, str] candidates returns correct EvaluationBatch."""
    adapter = TypedAdapter()
    candidate: dict[str, str] = {
        "system_prompt": "You are a helpful assistant.",
        "user_template": "Answer: {question}",
    }
    batch = ["question 1", "question 2", "question 3"]

    result = adapter.evaluate(batch, candidate)

    assert len(result.outputs) == 3
    assert len(result.scores) == 3
    assert result.trajectories is None


def test_typed_adapter_evaluate_with_traces():
    """evaluate() with capture_traces=True populates trajectories."""
    adapter = TypedAdapter()
    candidate: dict[str, str] = {
        "prompt": "Think step by step.",
    }
    batch = ["q1", "q2"]

    result = adapter.evaluate(batch, candidate, capture_traces=True)

    assert result.trajectories is not None
    assert len(result.trajectories) == 2


def test_typed_adapter_make_reflective_dataset():
    """make_reflective_dataset() returns records keyed by component name."""
    adapter = TypedAdapter()
    candidate: dict[str, str] = {
        "instruction": "Be concise.",
    }
    eval_batch = EvaluationBatch(outputs=["out"], scores=[0.5])

    dataset = adapter.make_reflective_dataset(candidate, eval_batch, ["instruction"])

    assert "instruction" in dataset
    assert len(dataset["instruction"]) == 1
    record = dataset["instruction"][0]
    assert "Inputs" in record
    assert "Feedback" in record


def test_propose_improvements_attribute_can_be_set():
    """propose_improvements can be assigned a callable matching ProposalFn."""

    def my_proposer(
        candidate: dict[str, str],
        reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
        components_to_update: list[str],
    ) -> dict[str, str]:
        return {name: f"improved: {candidate[name]}" for name in components_to_update if name in candidate}

    adapter = TypedAdapter()
    adapter.propose_improvements = my_proposer

    candidate: dict[str, str] = {"prompt": "original"}
    result = adapter.propose_improvements(candidate, {}, ["prompt"])

    assert "prompt" in result
    assert result["prompt"] == "improved: original"


def test_candidateT_defaults_to_str():
    """CandidateT defaults to str for dict[str, CandidateT] candidates."""

    class StringAdapter:
        def evaluate(
            self,
            batch: list[str],
            candidate: dict[str, str],
            capture_traces: bool = False,
        ) -> EvaluationBatch[str, str]:
            return EvaluationBatch(outputs=["out"] * len(batch), scores=[1.0] * len(batch))

        def make_reflective_dataset(
            self,
            candidate: dict[str, str],
            eval_batch: EvaluationBatch[str, str],
            components_to_update: list[str],
        ) -> Mapping[str, Sequence[Mapping[str, Any]]]:
            return {}

        propose_improvements = None

    adapter = StringAdapter()
    candidate: dict[str, CandidateT] = {"prompt": "You are helpful."}
    result = adapter.evaluate(["q1"], candidate)
    assert result.scores == [1.0]
    assert isinstance(candidate["prompt"], str)


def test_candidate_components_accessible_by_key():
    """String components in dict[str, CandidateT] are accessible by key."""
    candidate: dict[str, str] = {
        "system": "System prompt",
        "user": "User prompt",
    }
    assert candidate["system"] == "System prompt"
    assert candidate["user"] == "User prompt"
    assert list(candidate.keys()) == ["system", "user"]


def test_adapter_satisfies_gepa_adapter_protocol():
    """TypedAdapter has all the required GEPAAdapter attributes."""
    adapter = TypedAdapter()
    assert callable(adapter.evaluate)
    assert callable(adapter.make_reflective_dataset)
    assert hasattr(adapter, "propose_improvements")


def test_minimal_adapter_satisfies_gepa_adapter_protocol():
    """A minimal dict[str, str] adapter also satisfies the GEPAAdapter interface."""

    class MinimalAdapter:
        def evaluate(self, batch, candidate, capture_traces=False):
            return EvaluationBatch(outputs=[], scores=[])

        def make_reflective_dataset(self, candidate, eval_batch, components_to_update):
            return {}

        propose_improvements = None

    adapter = MinimalAdapter()
    assert callable(adapter.evaluate)
    assert callable(adapter.make_reflective_dataset)
    assert hasattr(adapter, "propose_improvements")
