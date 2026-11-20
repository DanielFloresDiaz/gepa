# Copyright (c) 2025 Lakshya A Agrawal and the GEPA contributors
# https://github.com/gepa-ai/gepa

"""Full valset evaluations name the iteration that produced the candidate."""

from __future__ import annotations

from typing import Any

from gepa import optimize
from gepa.core.adapter import EvaluationBatch


class _GrowingAdapter:
    """Every proposal appends one character; longer instructions score higher."""

    def evaluate(self, batch, candidate, capture_traces=False):
        score = min(1.0, len(candidate["comp"]) / 20)
        trajectories = [{"i": i} for i in range(len(batch))] if capture_traces else None
        return EvaluationBatch(outputs=[None] * len(batch), scores=[score] * len(batch), trajectories=trajectories)

    def make_reflective_dataset(self, candidate, eval_batch, components_to_update):
        return {name: [{"feedback": "longer"}] for name in components_to_update}

    def propose_improvements(self, candidate, reflective_dataset, components_to_update):
        return {name: candidate[name] + "x" for name in components_to_update}


class _Recorder:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def __getattr__(self, name: str):
        if not name.startswith("on_"):
            raise AttributeError(name)
        return lambda event: self.calls.append((name, dict(event)))

    def of(self, name: str) -> list[dict[str, Any]]:
        return [event for method, event in self.calls if method == name]


def test_parallel_full_evaluations_name_their_iteration():
    recorder = _Recorder()
    optimize(
        seed_candidate={"comp": "a"},
        trainset=list(range(4)),
        valset=list(range(3)),
        adapter=_GrowingAdapter(),
        max_metric_calls=60,
        reflection_minibatch_size=2,
        num_parallel_proposals=2,
        callbacks=[recorder],
        seed=0,
    )

    accepted = recorder.of("on_candidate_accepted")
    starts = recorder.of("on_full_evaluation_start")
    valset = [event for event in recorder.of("on_valset_evaluated") if event["iteration"] != 0]
    assert len(accepted) >= 2
    # One full evaluation per accepted candidate, announced with the candidate's own iteration.
    assert [event["iteration"] for event in starts] == [event["iteration"] for event in accepted]
    assert [event["iteration"] for event in valset] == [event["iteration"] for event in accepted]
    assert {event["source"] for event in starts} == {"reflective"}
    # Parallel batches give distinct iterations to the candidates of one batch.
    assert len({event["iteration"] for event in accepted}) == len(accepted)
    # The full evaluation start comes right before its valset result.
    names = [name for name, _ in recorder.calls if name in ("on_full_evaluation_start", "on_valset_evaluated")]
    assert names[0] == "on_valset_evaluated"  # the seed
    assert names[1:] == ["on_full_evaluation_start", "on_valset_evaluated"] * len(accepted)
