# Python Concurrency — Middle

Pick the model by workload:

| Workload | Usual starting point |
|---|---|
| Many network waits | `asyncio` |
| Blocking library I/O | threads |
| CPU-bound parallel work | processes or native/vectorized code |

Bound concurrency with a semaphore or worker pool. Every operation needs a timeout, cancellation path, and backpressure rule.
