# Scatter-Gather Aggregator - Senior

Fan-out amplifies tail latency, retries, connections, and failures.

| Control | Benefit | Cost |
|---|---|---|
| global deadline | bounded latency | partial answers |
| hedged request | lower tail | extra backend load |
| concurrency cap | protects dependencies | queueing |
| quorum `k-of-n` | tolerates failures | weaker completeness |
| per-shard circuit breaker | isolates bad shard | stale or missing data |

Monitor branch p99, aggregate p99, completion ratio, canceled work, hedge rate, and connection use. Test correlated slowness; independent-failure math is misleading when shards share a network or storage tier.

## Test yourself

1. When does hedging make an outage worse?
2. What contract describes partial results?
3. Why are correlated failures important?

Continue to [`professional.md`](professional.md).
