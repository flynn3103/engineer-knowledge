# Seams and Enabling Points — Professional

On a shared system, the difficult part is rarely writing an interface. It is introducing a boundary without breaking callers, deployments, builds, or other teams’ delivery plans.

## Treat a new seam as a delivery change

Before implementation, record the dependency owner, callers, configuration path, rollout plan, and removal date for compatibility code. Prefer a thin adapter owned by the consuming team over a shared abstraction committee.

## Safe rollout pattern

1. Add an injectable constructor or factory argument; retain the existing entry point.
2. Delegate the old path to the production implementation.
3. Add characterization and contract tests for the adapter.
4. Migrate consumers in independently shippable changes.
5. Observe errors, latency, and selected implementation after each rollout.
6. Delete the bridge when adoption is complete.

```python
class ReportService:
    def __init__(self, clock=None):
        self._clock = clock or SystemClock()
```

The default preserves existing callers; new callers and tests choose deliberately.

## Operating rules

- Keep configuration-based choices in one composition root and fail closed on invalid values.
- Run production and test build paths in CI when build-time substitution is unavoidable.
- Publish a small contract for cross-team adapters: inputs, outputs, errors, timeouts, and ownership.
- Avoid “universal” interfaces. They couple teams more tightly than the original dependency.
- Track temporary seams as migration work, not permanent architecture by accident.

## Evidence of success

- A consumer can test failures without a real external system.
- The dependency can be replaced or upgraded behind one adapter.
- Rollouts and rollback paths are documented and exercised.
- Teams can ship independently without coordinating every internal implementation change.
