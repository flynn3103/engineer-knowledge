# Async Runtimes - Senior

> Select and tune a runtime from workload shape, not benchmark folklore.

An async CDC service has at least four capacity domains: event-loop workers,
blocking workers, open connections, and downstream in-flight requests. Raising
only the first can increase contention while leaving the actual bottleneck
unchanged.

| Symptom | Likely cause | Evidence | Response |
|---|---|---|---|
| Kafka heartbeats late | Loop blocked | loop-lag histogram, task dump | offload/blocking API replacement |
| High latency, idle CPU | downstream saturation | in-flight and remote latency | bound concurrency, back off |
| Blocking queue grows | undersized pool or bad API | queue delay vs service time | isolate pool, remove blocking |
| High CPU, poor throughput | scheduler/contention overhead | profiles, run-queue depth | coarsen tasks, reduce workers |

Runtime ownership matters. Libraries should generally accept the application's
runtime rather than create nested loops. A Spark-side Python helper that starts
and stops a loop per record turns setup overhead into the dominant cost; a web
framework library that calls `asyncio.run()` under an existing loop fails
outright.

Use separate pools for slow metadata APIs and short filesystem calls when one
can starve the other. Put explicit bounds on each pool's queue: an unbounded
blocking queue merely moves overload out of sight.

Validate shutdown semantics. Stop admission, cancel or drain request scopes,
wait for bounded cleanup, then close pollers and executors. Closing the runtime
first can strand acknowledgements or object-store multipart uploads.

## Test yourself

1. Why can adding event-loop workers reduce throughput?
2. How would you isolate a slow legacy warehouse driver from Kafka heartbeats?
3. What shutdown order prevents accepted work from being stranded?

Continue to [`professional.md`](professional.md).
