# Async Programming Anti-patterns - Senior

> The most damaging anti-patterns combine blocking, cancellation gaps, and
> retries into feedback loops.

| Anti-pattern | Production failure | Correction |
|---|---|---|
| Sync-over-async | deadlock or thread starvation | async boundary end-to-end |
| Blocking call on loop | missed heartbeats, timer lag | native async or bounded offload |
| Timeout without work cancellation | abandoned work accumulates | propagate deadline to dependency |
| Immediate retries | synchronized retry storm | budget, backoff, jitter |
| Swallow cancellation | shutdown hangs | cleanup then re-raise cancellation |
| Global runtime/task | leaks across run lifetime | explicit application owner |

A Flink-adjacent async enrichment service can time out calls at 500 ms while its
blocking SDK continues for 30 seconds. Retrying each timeout creates up to 60
times more in-flight work than observed requests. A circuit breaker alone does
not reclaim already-started work; admission limits and dependency-level
cancellation are required.

Test overload, cancellation, and shutdown together. Happy-path load tests miss
the feedback loops that appear only when a dependency slows below timeout.

## Test yourself

1. How can a 500 ms timeout increase, rather than decrease, system occupancy?
2. Why should cancellation generally be re-raised after cleanup?
3. Which test reveals retries amplifying uncancellable blocking calls?

Continue to [`professional.md`](professional.md).
