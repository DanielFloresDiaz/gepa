# Copyright (c) 2025 Lakshya A Agrawal and the GEPA contributors
# https://github.com/gepa-ai/gepa

from typing import Any, Protocol, runtime_checkable

from gepa.core.data_loader import DataId
from gepa.core.state import GEPAState
from gepa.proposer.base import CandidateProposal


def per_example_score_improvement(proposal: CandidateProposal[Any, Any]) -> dict[DataId, float]:
    """Return per-example score deltas of ``proposal`` keyed by ``subsample_indices``.

    Empty score lists yield an empty dict.
    """
    return {
        proposal.subsample_indices[i]: proposal.subsample_scores_after[i] - proposal.subsample_scores_before[i]
        for i in range(len(proposal.subsample_indices))
    }


def mean_improvement(deltas: dict[DataId, float]) -> float:
    """Return the mean of ``deltas``, or ``0.0`` when empty."""
    if not deltas:
        return 0.0
    return sum(deltas.values()) / len(deltas)


def mean_score_improvement(proposal: CandidateProposal[Any, Any]) -> float:
    """Return the mean per-example score delta of ``proposal``.

    Empty or missing score lists are treated as a mean of ``0.0``. For aligned
    lists the sign matches a comparison of score *sums*.
    """
    return mean_improvement(per_example_score_improvement(proposal))


@runtime_checkable
class AcceptanceCriterion(Protocol):
    """Decides whether a proposed candidate should be accepted, and how much it improved.

    ``improvement`` returns one signed delta per aligned example keyed by
    ``DataId``. Built-in ``should_accept`` uses the mean of those deltas. After
    full evaluation the engine ranks with ``mean(parent_acceptance_scores) +
    mean(deltas)`` and places the instance front at
    ``mean(parent_acc[id]) + delta[id]``.

    The methods receive:

    - ``proposal``: the full ``CandidateProposal`` containing:

      - ``eval_before`` / ``eval_after``: ``SubsampleEvaluation`` objects with
        per-example ``scores``, ``outputs``, ``objective_scores``, and ``trajectories``.
      - ``subsample_scores_before`` / ``subsample_scores_after``: shorthand score lists.
      - ``subsample_indices``: ``DataId`` keys aligned with the score lists.
      - ``candidate``: the proposed candidate text.
      - ``parent_program_ids``: indices of parent candidates.
      - ``metadata``: free-form dict with LM prompts and raw outputs.

    - ``state``: the full ``GEPAState``, giving access to all existing candidates,
      validation scores, the Pareto frontier, iteration count, etc.
    """

    def improvement(
        self, proposal: CandidateProposal[Any, Any], state: GEPAState[Any, Any, Any]
    ) -> dict[DataId, float]:
        """Return per-example signed deltas of ``proposal`` vs its parent evaluation.

        Args:
            proposal: The full proposal including evaluation data, candidate, and metadata.
            state: The current optimization state.

        Returns:
            One delta per aligned example keyed by ``subsample_indices``.
            Positive favours the candidate on that example. The engine adds
            ``mean(deltas)`` to the mean of parent 1-centered acceptance scores
            and ``delta[id]`` to each parent's per-example acceptance score.
        """
        ...

    def should_accept(self, proposal: CandidateProposal[Any, Any], state: GEPAState[Any, Any, Any]) -> bool:
        """Return ``True`` if the proposed candidate should be accepted.

        Built-in criteria implement this as ``mean(improvement(...)) > 0`` (strict) or
        ``>= 0`` (equal-or-better). Custom criteria may use another aggregate
        (for example ``max``).

        Args:
            proposal: The full proposal including evaluation data, candidate, and metadata.
            state: The current optimization state.
        """
        ...


class StrictImprovementAcceptance:
    """Accept only if the mean subsample score strictly improves.

    This is the default acceptance criterion used by GEPA.
    """

    def improvement(
        self, proposal: CandidateProposal[Any, Any], state: GEPAState[Any, Any, Any]
    ) -> dict[DataId, float]:
        return per_example_score_improvement(proposal)

    def should_accept(self, proposal: CandidateProposal[Any, Any], state: GEPAState[Any, Any, Any]) -> bool:
        return mean_improvement(self.improvement(proposal, state)) > 0.0


class ImprovementOrEqualAcceptance:
    """Accept if the mean subsample score is greater than or equal to the old mean.

    Useful when you want to allow lateral moves that don't improve the score but
    may explore different regions of the solution space.
    """

    def improvement(
        self, proposal: CandidateProposal[Any, Any], state: GEPAState[Any, Any, Any]
    ) -> dict[DataId, float]:
        return per_example_score_improvement(proposal)

    def should_accept(self, proposal: CandidateProposal[Any, Any], state: GEPAState[Any, Any, Any]) -> bool:
        return mean_improvement(self.improvement(proposal, state)) >= 0.0
