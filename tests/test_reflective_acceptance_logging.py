# Copyright (c) 2025 Lakshya A Agrawal and the GEPA contributors
# https://github.com/gepa-ai/gepa

from unittest.mock import MagicMock

import pytest

from gepa.core.engine import GEPAEngine
from gepa.core.state import GEPAState, ValsetEvaluation
from gepa.proposer.base import CandidateProposal, SubsampleEvaluation
from gepa.strategies.acceptance import mean_improvement


class _RejectingComposite:
    """Reject when mean composite is negative even if raw score sums improve."""

    def improvement(self, proposal, state) -> dict[int, float]:
        return dict.fromkeys(proposal.subsample_indices, -0.1)

    def should_accept(self, proposal, state) -> bool:
        return mean_improvement(self.improvement(proposal, state)) > 0.0


def _minimal_engine(criterion, logger=None):
    return GEPAEngine(
        adapter=MagicMock(),
        run_dir=None,
        valset=None,
        seed_candidate={"prompt": "p"},
        perfect_score=None,
        seed=0,
        reflective_proposer=MagicMock(),
        merge_proposer=None,
        frontier_type="instance",
        logger=logger or MagicMock(),
        experiment_tracker=MagicMock(),
        acceptance_criterion=criterion,
    )


class TestReflectiveAcceptanceLogging:
    def test_custom_criterion_logs_mean_improvement_not_raw_sums(self):
        """Reject messages for custom criteria reference mean improvement, not score sums."""
        logger = MagicMock()
        engine = _minimal_engine(_RejectingComposite(), logger=logger)
        state = GEPAState(
            {"prompt": "seed"},
            ValsetEvaluation(outputs_by_val_id={0: "out"}, scores_by_val_id={0: 0.5}),
        )
        proposal = CandidateProposal(
            candidate={"prompt": "child"},
            parent_program_ids=[0],
            subsample_indices=[0],
            subsample_scores_before=[0.5],
            subsample_scores_after=[1.0],
            eval_before=SubsampleEvaluation(scores=[0.5], outputs=["old"]),
            eval_after=SubsampleEvaluation(scores=[1.0], outputs=["new"]),
            tag="reflective_mutation",
        )

        accepted = engine._accept_reflective_proposal(proposal, iteration=1, state=state)

        assert accepted is False
        logger.log.assert_called_once()
        message = logger.log.call_args[0][0]
        assert "mean improvement" in message
        assert "old_sum" not in message
        assert "new_sum" not in message
