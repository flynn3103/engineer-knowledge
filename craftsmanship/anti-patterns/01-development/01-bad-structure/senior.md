# Bad Structure Anti-Patterns — Senior

> Legacy structure is a delivery and reliability problem. Improve it without pausing the business or guessing about behavior.

## Goal

Create safe seams around high-risk code, migrate callers incrementally, and remove the organizational conditions that keep recreating the problem.

## Start with discovery

- Map owners, callers, data stores, jobs, and external contracts.
- Identify the change most likely to break customers, not the ugliest file.
- Collect characterization tests and production signals before changing behavior.
- Name the force behind the debt: unclear ownership, deadline pressure, missing review standards, or fear of deletion.

## Safe-change toolkit

| Tool | Use it when |
|---|---|
| Characterization tests | Existing behavior is unclear. |
| Facade or adapter | Callers need a stable interface during extraction. |
| Parallel change | A data or API contract must evolve without a flag day. |
| Feature flag | New behavior needs controlled rollout or rollback. |
| Strangler migration | A large component must be replaced in slices. |

```python
class LegacyOrders:
    def place(self, request):
        return self._old_place(request)


class OrdersFacade:
    def __init__(self, legacy, new_pricing):
        self.legacy = legacy
        self.new_pricing = new_pricing

    def place(self, request):
        request.total = self.new_pricing.quote(request)
        return self.legacy.place(request)
```

The facade creates a seam. Move one responsibility or caller through it at a time, measure errors, then delete the replaced path.

## Dismantle structural debt deliberately

1. Choose a narrow outcome, such as extracting pricing from an order manager.
2. Define invariants: totals, audit events, latency, and error behavior.
3. Add observability and a rollback path.
4. Migrate a small cohort; compare invariants.
5. Expand rollout, remove compatibility code, and record the new boundary.

For tangled flows, model legal states and transitions rather than moving nested conditions into different files. For dead code, run a time-boxed archaeology campaign: search, inspect telemetry, remove a small slice, and watch the relevant signals.

## Make decay harder to create

- Assign ownership to boundaries that many teams touch.
- Require small PRs and explicit deletion plans for replacements.
- Track hotspots by change frequency and defect rate, not file length alone.
- Fund structural work as risk reduction with measurable outcomes.

## Check your understanding

1. Which invariant makes your next extraction safe to roll out?
2. What would make you stop or roll back the migration?
3. Which team practice is producing the structural debt you see?
