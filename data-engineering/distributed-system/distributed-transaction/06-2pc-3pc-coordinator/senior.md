# Two-Phase and Three-Phase Commit - Senior

Prepared transactions consume locks, connections, WAL, and operator attention.

| Failure | Control |
|---|---|
| coordinator unavailable | replicated decision log |
| participant slow | deadline before prepare |
| prepared leak | age alert and resolution runbook |
| heuristic decision | reconciliation and explicit policy |
| many participants | redesign boundary or use Saga |

Monitor prepared count/age, lock wait, decision-log durability, phase latency, and recovery retries. Never automatically abort an unknown prepared transaction without proving the global decision.

## Test yourself

1. Why is timing out after prepare not enough to abort?
2. What resources remain pinned?
3. When is Saga a better boundary?

Continue to [`professional.md`](professional.md).
