"""Validation evaluation policy protocols and helpers."""

from __future__ import annotations

from abc import abstractmethod
from typing import Any, Protocol, runtime_checkable

from gepa.core.data_loader import DataId, DataInst, DataLoader
from gepa.core.state import GEPAState, ProgramIdx


@runtime_checkable
class EvaluationPolicy(Protocol[DataId, DataInst]):  # type: ignore
    """Strategy for choosing validation ids to evaluate and identifying best programs for validation instances."""

    @abstractmethod
    def get_eval_batch(
        self,
        loader: DataLoader[DataId, DataInst],
        state: GEPAState[Any, Any, Any],
        target_program_idx: ProgramIdx | None = None,
    ) -> list[DataId]:
        """Select examples for evaluation for a program"""
        ...

    @abstractmethod
    def get_best_program(self, state: GEPAState[Any, Any, Any]) -> ProgramIdx:
        """Return "best" program given all validation results so far across candidates"""
        ...

    @abstractmethod
    def get_valset_score(self, program_idx: ProgramIdx, state: GEPAState[Any, Any, Any]) -> float:
        """Return the program's ranking score on the valset.

        The default :class:`FullEvaluationPolicy` returns the 1-centered
        acceptance score. Custom policies may return another aggregate
        (for example the mean of raw scores on the evaluated subset).
        """
        ...


class FullEvaluationPolicy(EvaluationPolicy[DataId, DataInst]):
    """Policy that evaluates all validation instances every time."""

    def get_eval_batch(
        self,
        loader: DataLoader[DataId, DataInst],
        state: GEPAState[Any, Any, Any],
        target_program_idx: ProgramIdx | None = None,
    ) -> list[DataId]:
        """Always return the full ordered list of validation ids."""
        return list(loader.all_ids())

    def get_best_program(self, state: GEPAState[Any, Any, Any]) -> ProgramIdx:
        """Pick the program with the highest acceptance score (coverage as tie-break)."""
        best_idx, best_score, best_coverage = -1, float("-inf"), -1
        for program_idx, acc_score in enumerate(state.prog_candidate_acceptance_scores):
            coverage = len(state.prog_candidate_per_example_scores[program_idx])
            if acc_score > best_score or (acc_score == best_score and coverage > best_coverage):
                best_score = acc_score
                best_idx = program_idx
                best_coverage = coverage
        return best_idx

    def get_valset_score(self, program_idx: ProgramIdx, state: GEPAState[Any, Any, Any]) -> float:
        """Return the 1-centered acceptance score of the program (seed is 1.0)."""
        return state.prog_candidate_acceptance_scores[program_idx]


__all__ = [
    "DataLoader",
    "EvaluationPolicy",
    "FullEvaluationPolicy",
]
