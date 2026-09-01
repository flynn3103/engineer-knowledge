# Estimation — Middle

Build a model for ingress, processing, state, egress, and latency. Apply Little’s Law: concurrency is approximately throughput × time in system. At 2,000 requests/s and 100 ms, about 200 requests are in flight before queueing.

Split latency into network, queue, compute, database, and serialization budgets. Compare CPU, memory, connection, partition, and bandwidth constraints. Use load tests to calibrate coefficients rather than replace reasoning.

## Test yourself

1. How many operations are in flight at your target QPS and latency?
2. Which resource saturates first?
3. How does compression trade CPU for storage and egress?
4. Which benchmark result updates the model?

Continue to [`senior.md`](senior.md).
