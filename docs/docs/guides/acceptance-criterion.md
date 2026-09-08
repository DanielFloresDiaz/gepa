# Acceptance Criterion

Each iteration, GEPA evaluates a proposed candidate on a minibatch and decides whether to accept it into the candidate pool. The **acceptance criterion** controls this decision. By default, GEPA requires the mean minibatch score to strictly improve. You can change this by passing a different built-in strategy or implementing your own.

After a minibatch accept, GEPA always runs a full validation evaluation and adds the candidate. `improvement()` returns **one signed delta per aligned example** keyed by `DataId`. Ranking uses `mean(parent_acceptance_scores) + mean(deltas)`. The instance front uses `mean(parent_acc[id]) + delta[id]` (seed examples start at **1.0**). A reflective proposal has one parent; a merge uses the mean of all parents. Ranking values live on `result.val_acceptance_scores` and `result.val_per_example_acceptance_scores`. Raw per-example metric scores stay on `result.val_per_example_scores`.

---

## Built-in Criteria

Both built-ins share the same `improvement()`: per-example `after[id] − before[id]`. They differ only in `should_accept`, which uses the **mean** of those deltas.

### `"strict_improvement"` (default)

Accept only if the mean minibatch score strictly improves (`mean(improvement()) > 0`):

```python
result = gepa.optimize(
    ...,
    acceptance_criterion="strict_improvement",
)
```

### `"improvement_or_equal"`

Also accept lateral moves (`mean(improvement()) >= 0`). Useful for exploring different regions of the solution space when many candidates score the same:

```python
result = gepa.optimize(
    ...,
    acceptance_criterion="improvement_or_equal",
)
```

Along a lineage, score-sum deltas telescope to `1 + (candidate_raw[id] - seed_raw[id])` per example, so **who is best** still follows raw validation-mean order and **who wins each val example** still follows raw per-example order. The stored values are 1-centered, not the raw scores.

---

## Configuring in `optimize_anything`

```python
from gepa.optimize_anything import optimize_anything, GEPAConfig, EngineConfig

config = GEPAConfig(
    engine=EngineConfig(
        acceptance_criterion="improvement_or_equal",
    ),
)

result = optimize_anything(config=config, ...)
```

---

## Custom Criteria

Implement the `AcceptanceCriterion` protocol and pass an instance directly. Both methods are required:

- **`improvement(proposal, state) -> dict[DataId, float]`** — one signed delta per aligned example keyed by `subsample_indices`. The engine ranks with `mean(parent_acceptance_scores) + mean(deltas)` and places the instance front at `parent[id] + delta[id]`.
- **`should_accept(proposal, state) -> bool`** — typically `mean(deltas) > 0` (strict) or `>= 0` (equal-or-better). Custom criteria may use another aggregate such as `max`.

The methods receive:

- **`proposal`** — the full `CandidateProposal`, including `eval_before` and `eval_after` (`SubsampleEvaluation` objects with per-example `scores`, `outputs`, `objective_scores`, and `trajectories`).
- **`state`** — the full `GEPAState` (all candidates, validation scores, Pareto frontier, iteration count, etc.).

```python
from gepa.strategies.acceptance import AcceptanceCriterion, mean_improvement
from gepa.proposer.base import CandidateProposal
from gepa.core.state import GEPAState
```

### Example: accept if any minibatch example improves

The default uses the mean of all scores. A large regression on one example can mask improvements on others. If you want to accept whenever *at least one* example improved (regardless of regressions elsewhere):

```python
class AnyExampleImproved:
    def improvement(self, proposal: CandidateProposal, state: GEPAState) -> dict[int, float]:
        return {
            proposal.subsample_indices[i]: proposal.subsample_scores_after[i] - proposal.subsample_scores_before[i]
            for i in range(len(proposal.subsample_indices))
        }

    def should_accept(self, proposal: CandidateProposal, state: GEPAState) -> bool:
        deltas = self.improvement(proposal, state)
        return max(deltas.values()) > 0 if deltas else False
```

### Example: accept if any objective improves across the minibatch

When your evaluator returns multi-objective scores (via `side_info["scores"]`), you may want to accept a candidate that improves on *any single objective* aggregated across the minibatch — even if the blended score doesn't improve. This is useful for multi-objective optimization where you want the candidate pool to explore different trade-off directions:

```python
class AnyObjectiveImproved:
    """Accept if any objective's total across the minibatch increased."""

    def improvement(self, proposal: CandidateProposal, state: GEPAState) -> dict[int, float]:
        if proposal.eval_before is None or proposal.eval_after is None:
            return {}
        old_obj = proposal.eval_before.objective_scores
        new_obj = proposal.eval_after.objective_scores
        if old_obj is None or new_obj is None:
            return {
                proposal.subsample_indices[i]: proposal.subsample_scores_after[i] - proposal.subsample_scores_before[i]
                for i in range(len(proposal.subsample_indices))
            }

        deltas: dict[int, float] = {}
        for i in range(len(proposal.subsample_indices)):
            keys = set(old_obj[i]) | set(new_obj[i])
            best = 0.0
            for obj in keys:
                best = max(best, new_obj[i].get(obj, 0.0) - old_obj[i].get(obj, 0.0))
            deltas[proposal.subsample_indices[i]] = best
        return deltas

    def should_accept(self, proposal: CandidateProposal, state: GEPAState) -> bool:
        deltas = self.improvement(proposal, state)
        return max(deltas.values()) > 0 if deltas else False
```

```python
result = gepa.optimize(
    ...,
    acceptance_criterion=AnyObjectiveImproved(),
)
```

Every criterion uses `parent[id] + delta[id]` on the instance Pareto frontier (seed per-example scores start at 1.0). Ranking always uses the mean of the per-example deltas, even when `should_accept` uses `max`.

!!! note "Multi-objective scoring"
    To enable multi-objective tracking, return a `"scores"` dict inside `side_info` from your evaluator:

    ```python
    def evaluator(candidate, example):
        ...
        side_info = {
            "scores": {
                "accuracy": accuracy_score,
                "cost": cost_score,
            },
        }
        return score, side_info
    ```
