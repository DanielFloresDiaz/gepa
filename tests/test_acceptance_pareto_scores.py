# Copyright (c) 2025 Lakshya A Agrawal and the GEPA contributors
# https://github.com/gepa-ai/gepa

import pytest

import gepa
from gepa.core.adapter import EvaluationBatch
from gepa.core.engine import GEPAEngine
from gepa.core.result import GEPAResult
from gepa.core.state import SEED_ACCEPTANCE_SCORE, GEPAState, ValsetEvaluation
from gepa.strategies.acceptance import mean_improvement
from gepa.strategies.eval_policy import FullEvaluationPolicy


def _seed_eval(*, scores: dict[int, float], objectives=None) -> ValsetEvaluation:
    return ValsetEvaluation(
        outputs_by_val_id={vid: f"out{vid}" for vid in scores},
        scores_by_val_id=dict(scores),
        objective_scores_by_val_id=objectives,
    )


class TestSeedAcceptanceScores:
    def test_seed_acceptance_is_one(self):
        """Seed aggregate and per-example acceptance scores are centered at 1.0."""
        state = GEPAState({"prompt": "p"}, _seed_eval(scores={0: 0.2, 1: 0.8}))
        assert state.prog_candidate_acceptance_scores == [SEED_ACCEPTANCE_SCORE]
        assert state.prog_candidate_per_example_acceptance_scores == [{0: 1.0, 1: 1.0}]
        assert state.program_full_acceptance_scores_val_set == [1.0]
        assert state.program_raw_scores_val_set[0] == pytest.approx(0.5)

    def test_instance_frontier_centers_seed_at_one(self):
        """Instance front starts at 1.0 per example for every criterion."""
        state = GEPAState({"prompt": "p"}, _seed_eval(scores={0: 0.2, 1: 0.8}))
        assert state.pareto_front_valset == {0: 1.0, 1: 1.0}


class TestDerivedAcceptanceUpdate:
    def test_parent_plus_improvement_becomes_best(self):
        """A child with lower raw correctness can outrank the seed via derived scores."""
        state = GEPAState({"prompt": "p"}, _seed_eval(scores={0: 0.9, 1: 0.9}))
        child_eval = _seed_eval(scores={0: 0.4, 1: 0.4})
        state.update_state_with_new_program(
            parent_program_idx=[0],
            new_program={"prompt": "child"},
            valset_evaluation=child_eval,
            run_dir=None,
            num_metric_calls_by_discovery_of_new_program=0,
            acceptance_score=1.03,
            per_example_acceptance_scores={0: 1.03, 1: 1.03},
        )

        assert state.prog_candidate_acceptance_scores[0] == pytest.approx(1.0)
        assert state.prog_candidate_acceptance_scores[1] == pytest.approx(1.03)
        assert state.program_raw_scores_val_set[1] == pytest.approx(0.4)
        policy = FullEvaluationPolicy()
        assert policy.get_best_program(state) == 1
        assert policy.get_valset_score(1, state) == pytest.approx(1.03)
        assert state.program_at_pareto_front_valset[0] == {1}
        assert state.program_at_pareto_front_valset[1] == {1}

        result = GEPAResult.from_state(state)
        assert result.best_idx == 1
        assert result.val_acceptance_scores[0] == pytest.approx(1.0)
        assert result.val_per_example_scores[1] == {0: 0.4, 1: 0.4}
        assert result.val_per_example_acceptance_scores[1] == {0: 1.03, 1: 1.03}

    def test_per_example_delta_does_not_promote_lower_raw_child(self):
        """A child that lost the example (negative per-example delta) does not take the front."""
        state = GEPAState({"prompt": "p"}, _seed_eval(scores={0: 0.9}))
        child_eval = _seed_eval(scores={0: 0.4})
        state.update_state_with_new_program(
            parent_program_idx=[0],
            new_program={"prompt": "child"},
            valset_evaluation=child_eval,
            run_dir=None,
            num_metric_calls_by_discovery_of_new_program=0,
            acceptance_score=1.03,
            per_example_acceptance_scores={0: 1.0 + (0.4 - 0.9)},
        )
        assert state.program_at_pareto_front_valset[0] == {0}
        assert FullEvaluationPolicy().get_best_program(state) == 1


class _CompositeAlwaysBetter:
    """Accept every proposal and report a fixed positive composite improvement."""

    def improvement(self, proposal, state) -> dict[int, float]:
        return dict.fromkeys(proposal.subsample_indices, 0.03)

    def should_accept(self, proposal, state) -> bool:
        return True


class _DummyAdapter:
    def __init__(self):
        self.propose_improvements = self._propose_improvements

    def evaluate(self, batch, candidate, capture_traces=False):
        is_seed = candidate["system_prompt"] == "seed"
        score = 0.9 if is_seed else 0.4
        outputs = [{"id": item["id"], "score": score} for item in batch]
        scores = [score for _ in batch]
        trajectories = [{"score": s} for s in scores] if capture_traces else None
        return EvaluationBatch(outputs=outputs, scores=scores, trajectories=trajectories)

    def make_reflective_dataset(self, candidate, eval_batch, components_to_update):
        records = [{"score": score} for score in eval_batch.scores]
        return dict.fromkeys(components_to_update, records)

    def _propose_improvements(self, candidate, reflective_dataset, components_to_update):
        return dict.fromkeys(components_to_update, "child")


class _ImprovingAdapter:
    def __init__(self):
        self.propose_improvements = self._propose_improvements

    def evaluate(self, batch, candidate, capture_traces=False):
        is_seed = candidate["system_prompt"] == "seed"
        score = 0.2 if is_seed else 0.8
        outputs = [{"id": item["id"], "score": score} for item in batch]
        scores = [score for _ in batch]
        trajectories = [{"score": s} for s in scores] if capture_traces else None
        return EvaluationBatch(outputs=outputs, scores=scores, trajectories=trajectories)

    def make_reflective_dataset(self, candidate, eval_batch, components_to_update):
        records = [{"score": score} for score in eval_batch.scores]
        return dict.fromkeys(components_to_update, records)

    def _propose_improvements(self, candidate, reflective_dataset, components_to_update):
        return dict.fromkeys(components_to_update, "child")


def test_strict_improvement_ranking_follows_raw_mean_order(tmp_path):
    """StrictImprovement best_idx follows raw-mean order; stored aggregates are 1-centered."""
    trainset = [{"id": 0, "split": "train"}, {"id": 1, "split": "train"}]
    valset = [{"id": 0, "split": "val"}, {"id": 1, "split": "val"}]
    result = gepa.optimize(
        seed_candidate={"system_prompt": "seed"},
        trainset=trainset,
        valset=valset,
        adapter=_ImprovingAdapter(),
        reflection_lm=None,
        max_metric_calls=12,
        run_dir=str(tmp_path / "run"),
        skip_perfect_score=False,
        use_merge=False,
        candidate_selection_strategy="current_best",
    )

    seed_raw = sum(result.val_per_example_scores[0].values()) / len(result.val_per_example_scores[0])
    best_raw = sum(result.val_per_example_scores[result.best_idx].values()) / len(
        result.val_per_example_scores[result.best_idx]
    )
    assert result.val_acceptance_scores[0] == pytest.approx(1.0)
    assert result.best_idx != 0
    assert best_raw > seed_raw
    assert result.val_acceptance_scores[result.best_idx] == pytest.approx(1.0 + (best_raw - seed_raw))
    assert all(score == pytest.approx(0.8) for score in result.val_per_example_scores[result.best_idx].values())


def test_composite_criterion_lower_raw_score_can_become_best(tmp_path):
    """A custom criterion can rank a lower-correctness child above the seed."""
    trainset = [{"id": 0, "split": "train"}, {"id": 1, "split": "train"}]
    valset = [{"id": 0, "split": "val"}, {"id": 1, "split": "val"}]
    result = gepa.optimize(
        seed_candidate={"system_prompt": "seed"},
        trainset=trainset,
        valset=valset,
        adapter=_DummyAdapter(),
        reflection_lm=None,
        max_metric_calls=12,
        run_dir=str(tmp_path / "run"),
        skip_perfect_score=False,
        use_merge=False,
        acceptance_criterion=_CompositeAlwaysBetter(),
        candidate_selection_strategy="current_best",
    )

    assert result.val_acceptance_scores[0] == pytest.approx(1.0)
    assert result.best_idx != 0
    assert result.val_acceptance_scores[result.best_idx] > 1.0
    best_raw = result.val_per_example_scores[result.best_idx]
    assert all(score == pytest.approx(0.4) for score in best_raw.values())
    for front in result.per_val_instance_best_candidates.values():
        assert result.best_idx in front


class _FixedDelta:
    """Report a constant per-example improvement so parent-baseline choice is observable."""

    def improvement(self, proposal, state) -> dict[int, float]:
        return dict.fromkeys(proposal.subsample_indices, 0.05)

    def should_accept(self, proposal, state) -> bool:
        return True


def _minimal_engine(criterion=None):
    from unittest.mock import MagicMock

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
        logger=MagicMock(),
        experiment_tracker=MagicMock(),
        acceptance_criterion=criterion,
    )


def _state_with_two_parents():
    """Seed acc=1.0 plus a sibling with acc=1.4 and different raw scores."""
    state = GEPAState({"prompt": "seed"}, _seed_eval(scores={0: 0.9, 1: 0.9}))
    state.update_state_with_new_program(
        parent_program_idx=[0],
        new_program={"prompt": "other"},
        valset_evaluation=_seed_eval(scores={0: 0.1, 1: 0.1}),
        run_dir=None,
        num_metric_calls_by_discovery_of_new_program=0,
        acceptance_score=1.4,
        per_example_acceptance_scores={0: 1.4, 1: 1.4},
    )
    return state


class TestMeanParentAcceptance:
    def test_single_parent_matches_that_parent(self):
        """A one-parent proposal still uses that parent's acceptance score."""
        engine = _minimal_engine(_FixedDelta())
        state = _state_with_two_parents()
        child_eval = _seed_eval(scores={0: 0.5, 1: 0.5})
        parent_indices = engine._parent_indices([0])
        proposal = engine._full_eval_proposal(state, parent_indices, child_eval, {"prompt": "child"}, [0])
        deltas = engine.acceptance_criterion.improvement(proposal, state)
        score = engine._mean_parent_acceptance_score(state, parent_indices) + mean_improvement(deltas)
        assert parent_indices == [0]
        assert proposal.subsample_scores_before == [0.9, 0.9]
        assert score == pytest.approx(1.05)

    def test_merge_uses_mean_of_parent_acceptance_scores(self):
        """A merge child is mean(parent acceptance) + improvement, not the best parent."""
        engine = _minimal_engine(_FixedDelta())
        state = _state_with_two_parents()
        child_eval = _seed_eval(scores={0: 0.5, 1: 0.5})
        parent_indices = engine._parent_indices([0, 1])
        proposal = engine._full_eval_proposal(state, parent_indices, child_eval, {"prompt": "merge"}, [0, 1])
        deltas = engine.acceptance_criterion.improvement(proposal, state)
        score = engine._mean_parent_acceptance_score(state, parent_indices) + mean_improvement(deltas)
        assert score == pytest.approx(1.25)
        assert score != pytest.approx(1.45)

    def test_merge_proposal_averages_parent_raw_scores(self):
        """Full-eval improvement compares the child against the mean of parent raw scores."""
        engine = _minimal_engine()
        state = _state_with_two_parents()
        child_eval = _seed_eval(scores={0: 0.5, 1: 0.5})
        proposal = engine._full_eval_proposal(state, [0, 1], child_eval, {"prompt": "merge"}, [0, 1])
        assert proposal.subsample_scores_before == pytest.approx([0.5, 0.5])
        assert proposal.subsample_scores_after == pytest.approx([0.5, 0.5])
        assert engine.acceptance_criterion.improvement(proposal, state) == pytest.approx({0: 0.0, 1: 0.0})

    def test_merge_derived_subscores_average_parent_acceptance(self):
        """Custom instance-front scores start from the mean of parent per-example acceptance."""
        engine = _minimal_engine(_FixedDelta())
        state = _state_with_two_parents()
        derived = engine._derived_per_example_acceptance_scores(state, [0, 1], {0: 0.5, 1: 0.5}, {0: 0.05, 1: 0.05})
        assert derived[0] == pytest.approx(1.25)
        assert derived[1] == pytest.approx(1.25)

    def test_merge_proposal_averages_parent_objectives(self):
        """Per-example objective lists used for improvement are averaged across parents."""
        engine = _minimal_engine()
        state = GEPAState(
            {"prompt": "seed"},
            _seed_eval(scores={0: 1.0}, objectives={0: {"cost": -10.0, "acc": 1.0}}),
        )
        state.update_state_with_new_program(
            parent_program_idx=[0],
            new_program={"prompt": "other"},
            valset_evaluation=_seed_eval(scores={0: 0.0}, objectives={0: {"cost": -2.0, "acc": 0.0}}),
            run_dir=None,
            num_metric_calls_by_discovery_of_new_program=0,
            acceptance_score=1.2,
            per_example_acceptance_scores={0: 1.2},
        )
        child_eval = _seed_eval(scores={0: 0.5}, objectives={0: {"cost": -4.0, "acc": 0.5}})
        proposal = engine._full_eval_proposal(state, [0, 1], child_eval, {"prompt": "merge"}, [0, 1])
        assert proposal.eval_before is not None
        assert proposal.eval_before.objective_scores is not None
        assert proposal.eval_before.objective_scores[0]["cost"] == pytest.approx(-6.0)
        assert proposal.eval_before.objective_scores[0]["acc"] == pytest.approx(0.5)
        assert proposal.eval_after is not None
        assert proposal.eval_after.objective_scores == [{"cost": -4.0, "acc": 0.5}]


class TestDerivedAcceptanceFallback:
    def test_full_eval_parent_coverage_uses_mean_parent_plus_delta(self):
        """When every parent has the val_id, derived scores use mean parent + delta."""
        engine = _minimal_engine(_FixedDelta())
        state = GEPAState({"prompt": "seed"}, _seed_eval(scores={0: 0.9, 1: 0.9}))
        derived = engine._derived_per_example_acceptance_scores(state, [0], {0: 0.5, 1: 0.5}, {0: 0.05, 1: 0.05})
        assert derived[0] == pytest.approx(1.05)
        assert derived[1] == pytest.approx(1.05)

    def test_child_only_val_id_gets_seed_acceptance_score(self):
        """Incremental eval: child-only val_ids get SEED_ACCEPTANCE_SCORE with no parent delta."""
        engine = _minimal_engine(_FixedDelta())
        state = GEPAState({"prompt": "seed"}, _seed_eval(scores={0: 0.9, 1: 0.9}))
        derived = engine._derived_per_example_acceptance_scores(state, [0], {0: 0.5, 2: 0.5}, {0: 0.05})
        assert derived[0] == pytest.approx(1.05)
        assert derived[2] == SEED_ACCEPTANCE_SCORE
