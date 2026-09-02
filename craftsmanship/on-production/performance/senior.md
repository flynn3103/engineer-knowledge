# Performance — Senior

Use queueing theory and saturation evidence. Latency rises sharply near capacity; retries and synchronized work amplify tails. Set budgets across network, queue, compute, storage, and dependency segments.

Protect performance with regression tests, canaries, continuous profiling, and load tests that include failures and recovery. Optimize for throughput, latency, memory, and cost together; improving one can damage another.

## Test yourself

1. Why does latency become nonlinear near saturation?
2. Which budget segment dominates p99?
3. How do retries change the workload?
4. What regression belongs in CI versus a scheduled environment?

Continue to [`professional.md`](professional.md).
