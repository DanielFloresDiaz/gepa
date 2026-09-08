# Copyright (c) 2025 Lakshya A Agrawal and the GEPA contributors
# https://github.com/gepa-ai/gepa

"""Acceptance vs raw-aggregate wording in GEPA discovery logs."""

from unittest.mock import MagicMock

from gepa.core.state import ValsetEvaluation, initialize_gepa_state
from gepa.logging.utils import log_detailed_metrics_after_discovering_new_program
from gepa.strategies.eval_policy import FullEvaluationPolicy


class _RecordingTracker:
    def __init__(self):
        self.metrics: list[tuple[dict, int | None]] = []
        self.tables: list[tuple[str, list[str], list]] = []

    def log_metrics(self, metrics, step=None):
        self.metrics.append((dict(metrics), step))

    def log_table(self, table_name, columns, data):
        self.tables.append((table_name, list(columns), list(data)))


class _RawMeanPolicy(FullEvaluationPolicy):
    def get_valset_score(self, program_idx, state):
        return state.get_program_average_val_subset(program_idx)[0]


def _seed_state():
    return initialize_gepa_state(
        run_dir=None,
        logger=MagicMock(),
        seed_candidate={"prompt": "seed"},
        seed_valset_evaluation=ValsetEvaluation(
            outputs_by_val_id={0: "a", 1: "b"},
            scores_by_val_id={0: 0.2, 1: 0.8},
            objective_scores_by_val_id={0: {"acc": 0.2}, 1: {"acc": 0.8}},
        ),
        track_best_outputs=False,
    )


def test_discovery_logs_split_acceptance_from_raw_aggregate():
    """Stdout logs name acceptance, raw aggregate, and per-example series separately."""
    state = _seed_state()
    logger = MagicMock()
    tracker = _RecordingTracker()

    log_detailed_metrics_after_discovering_new_program(
        logger=logger,
        gepa_state=state,
        new_program_idx=0,
        valset_evaluation=ValsetEvaluation(
            outputs_by_val_id={},
            scores_by_val_id=dict(state.prog_candidate_per_example_scores[0]),
        ),
        objective_scores=state.prog_candidate_objective_scores[0],
        experiment_tracker=tracker,
        linear_pareto_front_program_idx=0,
        valset_size=2,
        val_evaluation_policy=FullEvaluationPolicy(),
        program_label="seed",
    )

    messages = [call.args[0] for call in logger.log.call_args_list]
    assert any("Raw valset aggregate for seed: 0.5" in msg for msg in messages)
    assert any("Acceptance score for seed: 1.0" in msg for msg in messages)
    assert any("Raw per-example scores for seed:" in msg for msg in messages)
    assert any("Per-example acceptance scores for seed:" in msg for msg in messages)
    assert any("Instance Pareto front (per-example acceptance):" in msg for msg in messages)
    assert any("Best acceptance score so far: 1.0" in msg for msg in messages)
    assert not any("Valset score for" in msg for msg in messages)
    assert not any("Val acceptance for" in msg for msg in messages)


def test_discovery_tracker_metrics_include_acceptance_raw_and_legacy_aliases():
    """Tracker metrics expose acceptance and raw aggregate, and keep legacy aliases.

    Fresh state starts at i=-1, so seed discovery is logged at step 0.
    """
    state = _seed_state()
    tracker = _RecordingTracker()

    log_detailed_metrics_after_discovering_new_program(
        logger=MagicMock(),
        gepa_state=state,
        new_program_idx=0,
        valset_evaluation=ValsetEvaluation(
            outputs_by_val_id={},
            scores_by_val_id=dict(state.prog_candidate_per_example_scores[0]),
        ),
        objective_scores=state.prog_candidate_objective_scores[0],
        experiment_tracker=tracker,
        linear_pareto_front_program_idx=0,
        valset_size=2,
        val_evaluation_policy=FullEvaluationPolicy(),
    )

    metrics, step = tracker.metrics[0]
    assert step == 0
    assert metrics["val_acceptance_score"] == 1.0
    assert metrics["val_raw_aggregate"] == 0.5
    assert metrics["best_acceptance_score_on_valset"] == 1.0
    assert metrics["val_program_average"] == metrics["val_acceptance_score"]
    assert metrics["best_score_on_valset"] == metrics["best_acceptance_score_on_valset"]
    assert metrics["valset_pareto_front_agg"] == metrics["valset_pareto_front_acceptance"]
    assert metrics["objective/acc"] == 0.5


def test_discovery_tables_split_raw_scores_from_per_example_acceptance():
    """valset_scores stays raw; valset_acceptance_scores stores per-example acceptance."""
    state = _seed_state()
    tracker = _RecordingTracker()

    log_detailed_metrics_after_discovering_new_program(
        logger=MagicMock(),
        gepa_state=state,
        new_program_idx=0,
        valset_evaluation=ValsetEvaluation(
            outputs_by_val_id={},
            scores_by_val_id=dict(state.prog_candidate_per_example_scores[0]),
        ),
        objective_scores=state.prog_candidate_objective_scores[0],
        experiment_tracker=tracker,
        linear_pareto_front_program_idx=0,
        valset_size=2,
        val_evaluation_policy=FullEvaluationPolicy(),
    )

    tables = {name: (columns, data) for name, columns, data in tracker.tables}
    assert "valset_scores" in tables
    assert "valset_acceptance_scores" in tables
    raw_row = tables["valset_scores"][1][0]
    acc_row = tables["valset_acceptance_scores"][1][0]
    assert raw_row[2:] == [0.2, 0.8]
    assert acc_row[2:] == [1.0, 1.0]


def test_custom_policy_logs_policy_score_when_it_differs_from_acceptance():
    """A policy that returns raw mean still logs acceptance, plus a policy-score line."""
    state = _seed_state()
    logger = MagicMock()

    log_detailed_metrics_after_discovering_new_program(
        logger=logger,
        gepa_state=state,
        new_program_idx=0,
        valset_evaluation=ValsetEvaluation(
            outputs_by_val_id={},
            scores_by_val_id=dict(state.prog_candidate_per_example_scores[0]),
        ),
        objective_scores=None,
        experiment_tracker=_RecordingTracker(),
        linear_pareto_front_program_idx=0,
        valset_size=2,
        val_evaluation_policy=_RawMeanPolicy(),
    )

    messages = [call.args[0] for call in logger.log.call_args_list]
    assert any("Acceptance score for new program: 1.0" in msg for msg in messages)
    assert any("Policy valset score for new program: 0.5" in msg for msg in messages)
    assert any("Best policy valset score: 0.5" in msg for msg in messages)
