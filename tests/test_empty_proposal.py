# Copyright (c) 2025 Lakshya A Agrawal and the GEPA contributors
# https://github.com/gepa-ai/gepa

"""Empty propose_improvements results must skip child minibatch evaluation."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from gepa.core.adapter import EvaluationBatch
from gepa.proposer.reflective_mutation.reflective_mutation import (
    ProposalContext,
    ReflectiveMutationProposer,
)


class _EmptyProposalAdapter:
    """Adapter that always returns an empty improvement map."""

    def evaluate(self, batch, candidate, capture_traces=False):
        trajectories = [{"trace": i} for i in range(len(batch))] if capture_traces else None
        return EvaluationBatch(
            outputs=[f"out_{i}" for i in range(len(batch))],
            scores=[0.5] * len(batch),
            trajectories=trajectories,
        )

    def make_reflective_dataset(self, candidate, eval_batch, components_to_update):
        return {name: [{"feedback": "x"}] for name in components_to_update}

    def propose_improvements(self, candidate, reflective_dataset, components_to_update):
        return {}


def test_empty_proposal_skips_child_evaluation():
    """When propose_improvements returns {}, do not re-evaluate an identical candidate."""
    adapter = _EmptyProposalAdapter()
    evaluate_calls: list[dict[str, Any]] = []
    original_evaluate = adapter.evaluate

    def _tracking_evaluate(batch, candidate, capture_traces=False):
        evaluate_calls.append({"capture_traces": capture_traces, "candidate": candidate})
        return original_evaluate(batch, candidate, capture_traces=capture_traces)

    adapter.evaluate = _tracking_evaluate  # type: ignore[method-assign]

    logger = MagicMock()
    experiment_tracker = MagicMock()
    proposer = ReflectiveMutationProposer(
        logger=logger,
        trainset=["ex0"],
        adapter=adapter,
        candidate_selector=MagicMock(),
        module_selector=lambda *_args, **_kwargs: ["comp"],
        batch_sampler=MagicMock(),
        perfect_score=None,
        skip_perfect_score=False,
        experiment_tracker=experiment_tracker,
        reflection_lm=None,
    )

    curr_prog = {"comp": "seed"}
    ctx = ProposalContext(
        iteration=1,
        curr_prog_id=0,
        curr_prog=curr_prog,
        curr_prog_score=0.5,
        subsample_ids=[0],
        minibatch=["ex0"],
        parent_ids=[0],
        is_seed_candidate=True,
    )
    state = MagicMock()

    output = proposer.execute_proposal(ctx, state)

    assert output.proposal is None
    # Parent eval only — no child eval after empty proposal.
    assert len(evaluate_calls) == 1
    assert evaluate_calls[0]["capture_traces"] is True
    logger.log.assert_any_call("Iteration 1: Empty proposal (no component updates). Skipping.")
