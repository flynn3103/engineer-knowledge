# Evaluation and Execution Models — Senior

Production behavior depends on cancellation, backpressure, stack growth, exception unwinding, scheduler fairness, and memory ordering. Treat execution mode as a workload decision. Profile event-loop lag, runnable work, compilation, deoptimization, and queue depth.

## Test yourself

1. What happens when blocking I/O runs on an event loop?
2. Which state is restored after deoptimization?
3. How can laziness move a failure far from its cause?

Continue to [`professional.md`](professional.md).
