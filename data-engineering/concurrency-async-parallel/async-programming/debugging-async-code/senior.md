# Debugging Async Code - Senior

> Distinguish deadlock, starvation, overload, and a merely slow dependency.

| Incident shape | Signature | Confirmation |
|---|---|---|
| Async deadlock | stable wait cycle, no progress | task wait-for graph |
| Loop starvation | timer lag, long callbacks | CPU profile + slow callback data |
| Pool starvation | queued blocking work, all workers occupied | thread/task dumps |
| Downstream stall | tasks await same remote operation | dependency traces/metrics |
| Cancellation race | result and cancel arrive together | event timeline and state transitions |

For an Airflow triggerer that stops firing events, capture task and thread dumps
before restart. A task graph may show all triggers waiting normally while one
synchronous callback monopolizes the loop; that is starvation, not deadlock.

Reproduce races with deterministic barriers rather than sleeps. Place hooks
before completion, cancellation, and cleanup, then force each ordering. Verify
that exactly one terminal outcome wins and resource cleanup is idempotent.

Sample long-lived task stacks and retain the oldest task age. Full per-task
logging at high cardinality can itself overload the process and obscure the
original issue.

## Test yourself

1. How does loop starvation differ from an async deadlock in task dumps?
2. Why are sleeps weak tools for reproducing cancellation races?
3. What bounded telemetry would expose leaked long-lived tasks?

Continue to [`professional.md`](professional.md).
