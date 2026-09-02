# Performance — Middle

Use CPU profiles and flame graphs for on-CPU work, allocation profiles for churn, memory profiles for retention, and tracing for waiting across components. Separate CPU-bound, I/O-bound, lock-bound, and queue-bound behavior.

Benchmark data structures and concurrency with realistic sizes. More workers can reduce latency until locks, connection pools, cache misses, or downstream limits dominate.

## Test yourself

1. Which profile distinguishes churn from retention?
2. How does contention appear as concurrency rises?
3. Why can a faster function leave endpoint latency unchanged?
4. What is the bottleneck after your optimization?

Continue to [`senior.md`](senior.md).
