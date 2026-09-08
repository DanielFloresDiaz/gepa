from gepa.core.result import GEPAResult


def test_gepa_result_from_dict_upcasts_version0():
    legacy_payload = {
        "candidates": [{"system_prompt": "weight=0"}, {"system_prompt": "weight=1"}],
        "parents": [[None], [0]],
        "val_aggregate_scores": [0.15, 0.35],
        "val_subscores": [[0.1, 0.2], [0.3, 0.4]],
        "per_val_instance_best_candidates": [[0], [1]],
        "discovery_eval_counts": [0, 2],
        "best_outputs_valset": [
            [(0, {"value": 0.1})],
            [(1, {"value": 0.4})],
        ],
        "total_metric_calls": 5,
        "num_full_val_evals": 2,
        "run_dir": "/tmp/gepa",
        "seed": 42,
    }

    result = GEPAResult.from_dict(legacy_payload)

    assert result.val_acceptance_scores == [0.15, 0.35]
    assert result.val_per_example_scores == [{0: 0.1, 1: 0.2}, {0: 0.3, 1: 0.4}]
    assert result.val_per_example_acceptance_scores[0] == {0: 1.0, 1: 1.0}
    assert result.per_val_instance_best_candidates == {0: {0}, 1: {1}}
    assert result.best_outputs_valset == {
        0: [(0, {"value": 0.1})],
        1: [(1, {"value": 0.4})],
    }

    serialized = result.to_dict()
    assert serialized["validation_schema_version"] == GEPAResult._VALIDATION_SCHEMA_VERSION
    assert "val_acceptance_scores" in serialized
    assert "val_per_example_scores" in serialized
    assert "val_per_example_acceptance_scores" in serialized
    assert "val_aggregate_scores" not in serialized
    assert "val_subscores" not in serialized


def test_gepa_result_from_dict_upcasts_version2():
    payload = {
        "validation_schema_version": 2,
        "candidates": [{"system_prompt": "seed"}, {"system_prompt": "child"}],
        "parents": [[None], [0]],
        "val_aggregate_scores": [1.0, 1.2],
        "val_subscores": [{0: 0.5, 1: 0.5}, {0: 0.7, 1: 0.7}],
        "per_val_instance_best_candidates": {0: [1], 1: [1]},
        "discovery_eval_counts": [0, 2],
    }

    result = GEPAResult.from_dict(payload)

    assert result.val_acceptance_scores == [1.0, 1.2]
    assert result.val_per_example_scores == [{0: 0.5, 1: 0.5}, {0: 0.7, 1: 0.7}]
    assert result.val_per_example_acceptance_scores[0] == {0: 1.0, 1: 1.0}
    assert result.val_per_example_acceptance_scores[1][0] == 1.2
    assert result.val_per_example_acceptance_scores[1][1] == 1.2
