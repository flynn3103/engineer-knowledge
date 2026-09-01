# Python Concurrency — Senior

Concurrency design is resource management.

- Bound queues and record rejection or wait time.
- Avoid unstructured background tasks; own and await task lifecycles.
- Design idempotency before parallel retries.
- Separate CPU pools from latency-sensitive event loops.
- Load-test saturation, cancellation, and dependency slowdown.

Use traces and queue metrics to decide where concurrency is actually needed.
