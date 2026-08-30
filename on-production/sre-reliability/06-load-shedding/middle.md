# Load Shedding — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Can you implement and test a priority-aware admission policy across an API and its worker queue?

---

## Compose the controls

Use admission control before scarce work begins, bounded queues to prevent memory growth, timeouts to release resources, and concurrency limits to protect dependencies. These controls complement each other; a queue without admission merely delays rejection.

## Policy choices

| Approach | Best when | Risk |
|---|---|---|
| Per-client limit | A few clients dominate | Identity must be trusted |
| Priority queue | Work classes are explicit | Low priority can starve |
| Global concurrency cap | Dependency has hard limit | Can reject healthy traffic |
| Probabilistic shed | Load is broad and uniform | Harder to explain to clients |

## Scenario

Search and checkout share a database pool. Add separate concurrency budgets so search spikes cannot consume checkout connections. At the gateway, search receives `429` with a retry-after value; workers stop accepting report jobs at 80% queue depth. Test the full path with load and verify checkout success, not only gateway rejection.

## Incremental rollout

First record what would be rejected. Then enable shedding for an expendable class in one region. Add dashboards for queue age, rejected requests, retries, and protected-journey success. Remove rules that do not demonstrably protect a bottleneck.

## Apply it

1. Draw resource budgets for two request classes.
2. Choose admission and queue thresholds with a rationale.
3. Run a load test that overloads one class only.

## Verify your work

- The protected class keeps its latency and success target.
- Queue age remains bounded under overload.
- Retried requests do not recreate the same load spike.

## Review questions

- Why use both admission control and bounded queues?
- How can a priority queue cause starvation?
- Which user-facing metric proves shedding worked?
