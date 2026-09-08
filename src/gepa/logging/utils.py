# Copyright (c) 2025 Lakshya A Agrawal and the GEPA contributors
# https://github.com/gepa-ai/gepa


from typing import Any

from gepa.core.adapter import DataInst
from gepa.core.data_loader import DataId
from gepa.core.state import GEPAState, ValsetEvaluation
from gepa.strategies.eval_policy import EvaluationPolicy


def _raw_aggregate(scores_by_val_id: dict[Any, float]) -> tuple[float, int]:
    coverage = len(scores_by_val_id)
    if coverage == 0:
        return float("-inf"), 0
    return sum(scores_by_val_id.values()) / coverage, coverage


def log_detailed_metrics_after_discovering_new_program(
    logger,
    gepa_state: GEPAState[Any, Any, Any],
    new_program_idx,
    valset_evaluation: ValsetEvaluation,
    objective_scores,
    experiment_tracker,
    linear_pareto_front_program_idx,
    valset_size: int,
    val_evaluation_policy: EvaluationPolicy[DataId, DataInst],
    program_label: str = "new program",
):
    """Log acceptance vs raw-aggregate scores after a candidate is added.

    Acceptance is the 1-centered ranking score (seed is 1.0). Raw aggregate is
    the mean of per-example metric scores from the adapter. Instance Pareto
    values are per-example acceptance, not raw metrics.
    """
    iteration = gepa_state.i + 1
    best_program_idx = val_evaluation_policy.get_best_program(gepa_state)
    policy_score = val_evaluation_policy.get_valset_score(new_program_idx, gepa_state)
    best_policy_score = val_evaluation_policy.get_valset_score(best_program_idx, gepa_state)

    acceptance_score = gepa_state.prog_candidate_acceptance_scores[new_program_idx]
    per_example_acceptance = gepa_state.prog_candidate_per_example_acceptance_scores[new_program_idx]
    raw_per_example = dict(valset_evaluation.scores_by_val_id)
    raw_aggregate, coverage = _raw_aggregate(raw_per_example)
    best_acceptance = max(gepa_state.program_full_acceptance_scores_val_set)

    logger.log(
        f"Iteration {iteration}: Raw valset aggregate for {program_label}: {raw_aggregate}"
        f" (coverage {coverage} / {valset_size})"
    )
    logger.log(f"Iteration {iteration}: Acceptance score for {program_label}: {acceptance_score}")
    if policy_score != acceptance_score:
        logger.log(f"Iteration {iteration}: Policy valset score for {program_label}: {policy_score}")
    logger.log(f"Iteration {iteration}: Raw per-example scores for {program_label}: {raw_per_example}")
    logger.log(f"Iteration {iteration}: Per-example acceptance scores for {program_label}: {per_example_acceptance}")
    if objective_scores:
        logger.log(f"Iteration {iteration}: Objective aggregate scores for {program_label}: {objective_scores}")
    logger.log(f"Iteration {iteration}: Instance Pareto front (per-example acceptance): {gepa_state.pareto_front_valset}")
    if gepa_state.objective_pareto_front:
        logger.log(f"Iteration {iteration}: Objective Pareto front scores: {gepa_state.objective_pareto_front}")

    pareto_scores = list(gepa_state.pareto_front_valset.values())
    assert all(score > float("-inf") for score in pareto_scores), (
        "Should have at least one valid score per validation example"
    )
    assert len(pareto_scores) > 0
    pareto_avg = sum(pareto_scores) / len(pareto_scores)

    logger.log(f"Iteration {iteration}: Instance Pareto front mean acceptance: {pareto_avg}")
    logger.log(f"Iteration {iteration}: Updated instance Pareto front programs: {gepa_state.program_at_pareto_front_valset}")
    if gepa_state.program_at_pareto_front_objectives:
        logger.log(
            f"Iteration {iteration}: Updated objective Pareto front programs: {gepa_state.program_at_pareto_front_objectives}"
        )
    logger.log(f"Iteration {iteration}: Best acceptance score so far: {best_acceptance}")
    logger.log(f"Iteration {iteration}: Best program as per acceptance score: {best_program_idx}")
    if best_policy_score != best_acceptance:
        logger.log(f"Iteration {iteration}: Best policy valset score: {best_policy_score}")
    logger.log(f"Iteration {iteration}: Linear Pareto front program index: {linear_pareto_front_program_idx}")
    logger.log(f"Iteration {iteration}: {program_label} candidate index: {new_program_idx}")

    # Scalar metrics go to log_metrics (creates wandb/mlflow line charts).
    # New names distinguish acceptance (ranking) from raw aggregate (metric mean).
    # Legacy keys keep existing dashboards working; they alias the acceptance series.
    metrics = {
        "iteration": iteration,
        "new_program_idx": new_program_idx,
        "val_acceptance_score": acceptance_score,
        "val_raw_aggregate": raw_aggregate,
        "best_acceptance_score_on_valset": best_acceptance,
        "valset_pareto_front_acceptance": pareto_avg,
        "best_program_as_per_acceptance_score_valset": best_program_idx,
        "val_evaluated_count_new_program": coverage,
        "val_total_count": valset_size,
        "total_metric_calls": gepa_state.total_num_evals,
        "val_program_average": acceptance_score,
        "best_score_on_valset": best_acceptance,
        "valset_pareto_front_agg": pareto_avg,
        "best_program_as_per_agg_score_valset": best_program_idx,
    }
    if objective_scores:
        for obj_name, obj_val in objective_scores.items():
            if isinstance(obj_val, int | float):
                metrics[f"objective/{obj_name}"] = obj_val
    experiment_tracker.log_metrics(metrics, step=iteration)

    # Structured data goes to log_table (creates wandb Tables / mlflow artifacts)
    # instead of log_metrics, which would flatten nested dicts into hundreds of charts.
    # Only log the new candidate's row to avoid O(candidates * valset) repeated uploads.

    all_val_ids = sorted(gepa_state.pareto_front_valset.keys(), key=str)
    val_columns = ["candidate_idx", "parent_ids"] + [str(vid) for vid in all_val_ids]
    new_parent = gepa_state.parent_program_for_candidate[new_program_idx]

    raw_scores_dict = gepa_state.prog_candidate_per_example_scores[new_program_idx]
    raw_row = [new_program_idx, str(new_parent)] + [raw_scores_dict.get(vid) for vid in all_val_ids]
    experiment_tracker.log_table("valset_scores", columns=val_columns, data=[raw_row])

    acceptance_row = [new_program_idx, str(new_parent)] + [per_example_acceptance.get(vid) for vid in all_val_ids]
    experiment_tracker.log_table("valset_acceptance_scores", columns=val_columns, data=[acceptance_row])

    # Instance Pareto front: which programs are best for which val examples (acceptance)
    pareto_front_rows = [
        [str(val_id), score, str(sorted(gepa_state.program_at_pareto_front_valset[val_id]))]
        for val_id, score in gepa_state.pareto_front_valset.items()
    ]
    if pareto_front_rows:
        experiment_tracker.log_table(
            "valset_pareto_front",
            columns=["val_id", "best_score", "program_ids"],
            data=pareto_front_rows,
        )

    # Objective scores for the new candidate only (per-objective aggregates, not acceptance)
    new_obj_scores = gepa_state.prog_candidate_objective_scores[new_program_idx]
    if new_obj_scores:
        all_objectives = sorted(new_obj_scores.keys(), key=str)
        obj_columns = ["candidate_idx", "parent_ids"] + [str(obj) for obj in all_objectives]
        obj_row = [new_program_idx, str(new_parent)] + [new_obj_scores.get(obj) for obj in all_objectives]
        experiment_tracker.log_table("objective_scores", columns=obj_columns, data=[obj_row])

    if gepa_state.objective_pareto_front:
        obj_pareto_rows = [
            [str(obj), float(score), str(sorted(gepa_state.program_at_pareto_front_objectives[obj]))]
            for obj, score in gepa_state.objective_pareto_front.items()
        ]
        experiment_tracker.log_table(
            "objective_pareto_front",
            columns=["objective", "best_score", "program_ids"],
            data=obj_pareto_rows,
        )
