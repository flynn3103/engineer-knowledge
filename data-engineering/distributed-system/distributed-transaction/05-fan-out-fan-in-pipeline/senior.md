# Fan-Out/Fan-In Pipeline - Senior

Capacity must be bounded across the complete pipeline, not independently at each stage.

| Risk | Control |
|---|---|
| goroutine leak | structured cancellation |
| slow sink | bounded channel backpressure |
| global overload | shared semaphore |
| one poison item | explicit error policy |
| reordered output | sequence buffer or partition-local order |

Measure in-flight work, queue age, blocked sends, goroutines, memory, and downstream saturation. Inject early sink exit and timeout to prove every worker terminates.

## Test yourself

1. Why can per-stage limits exceed a global resource limit?
2. How do you prove no worker leaked?
3. When is unordered output preferable?

Continue to [`professional.md`](professional.md).
