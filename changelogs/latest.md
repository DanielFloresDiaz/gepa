# Changelog

## [0.2.0] - 2026-09-09

This release introduces a clearer acceptance-scoring model, renames several public APIs for consistency, and removes in-repo DSPy adapters in favor of the DSPy framework integration.

**Optimization engine and strategies:**

* Acceptance criteria now compare the mean per-example subsample score instead of the sum, so acceptance behavior is scale-invariant across minibatch sizes.
* Candidates are ranked with 1-centered acceptance scores that track improvement relative to parents; raw metric aggregates are logged separately for interpretability.
* Candidate selectors and the Pareto frontier use acceptance scores instead of raw aggregate scores.
* Custom acceptance criteria must implement an `improvement()` method that returns per-example deltas; built-in criteria derive acceptance from the mean of those deltas.

**API surface (`optimize`, callbacks, results):**

* Renamed `module_selector` to `component_selector` and `custom_candidate_proposer` to `custom_component_proposer`; the old names remain as deprecated aliases.
* `GEPAResult` exposes `val_acceptance_scores`, `val_per_example_scores`, and `val_per_example_acceptance_scores` in place of `val_aggregate_scores` and `val_subscores`, with serialization migration for saved results.
* `on_proposal_end` events use `proposed_improvements` instead of `new_instructions` (the old field is still populated but deprecated).
* `on_valset_evaluated` events now include `acceptance_score` and `raw_aggregate` fields.

**Adapters and integrations:**

* Removed the in-repo `dspy_adapter` and `dspy_full_program_adapter` packages; use [`dspy.GEPA`](https://dspy.ai/tutorials/gepa_ai_program/) for DSPy program optimization.

**Configuration and docs:**

* Updated guides for acceptance criteria, candidate selection, adapters, and callbacks to reflect the new terminology and scoring model.
* Removed the Claude Code CLI proposer guide.
