# Copyright (c) 2025 Lakshya A Agrawal and the GEPA contributors
# https://github.com/gepa-ai/gepa

from dataclasses import dataclass, field
from typing import Any, Generic, Protocol

from gepa.core.adapter import CandidateT
from gepa.core.data_loader import DataId
from gepa.core.state import GEPAState


@dataclass
class SubsampleEvaluation:
    """Result of evaluating a candidate on the subsample minibatch.

    Captures all outputs from ``adapter.evaluate``:

    - ``scores``: per-example numeric scores.
    - ``outputs``: per-example raw outputs (e.g. the model's response text).
    - ``objective_scores``: optional per-example multi-objective score dicts.
    - ``trajectories``: optional per-example execution traces (captured for both
      before and after evaluations).
    """

    scores: list[float]
    outputs: list[Any] = field(default_factory=list)
    objective_scores: list[dict[str, float]] | None = None
    trajectories: list[Any] | None = None


@dataclass
class CandidateProposal(Generic[DataId, CandidateT]):
    candidate: dict[str, CandidateT]
    parent_program_ids: list[int]
    subsample_indices: list[DataId]
    subsample_scores_before: list[float]
    subsample_scores_after: list[float]
    # Rich evaluation data (superset of scores — includes outputs, objective_scores, trajectories)
    eval_before: SubsampleEvaluation | None = None
    eval_after: SubsampleEvaluation | None = None
    # Free-form metadata for logging/trace
    tag: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        n_indices = len(self.subsample_indices)
        n_before = len(self.subsample_scores_before)
        n_after = len(self.subsample_scores_after)
        if n_before != n_indices or n_after != n_indices:
            raise ValueError(
                "subsample_indices length "
                f"({n_indices}) must match subsample_scores_before ({n_before}) "
                f"and subsample_scores_after ({n_after})"
            )


class ProposeNewCandidate(Protocol[DataId]):
    """
    Strategy that receives the current optimizer state and proposes a new candidate or returns None.
    It may compute subsample evaluations, set trace fields in state, etc.
    The engine will handle acceptance and full eval unless the strategy already did those and encoded in metadata.
    """

    def propose(self, state: GEPAState[Any, DataId, Any]) -> CandidateProposal | None: ...
