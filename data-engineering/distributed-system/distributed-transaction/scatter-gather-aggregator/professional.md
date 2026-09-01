# Scatter-Gather Aggregator - Professional

Scatter-gather is a latency-budget allocation and admission-control problem.

## Real systems

- Elasticsearch's coordinating node routes shard requests and reduces shard-level top-k results.
- Cassandra coordinators gather replica responses according to consistency level.
- Google's Tail at Scale work describes delayed hedging and tied requests.
- gRPC deadlines propagate cancellation metadata but applications must stop work cooperatively.

At 100-way fan-out, even 99% per-branch success gives only about 37% probability that all branches succeed. Dashboard per-branch latency, aggregate completion policy, deadline exhaustion, canceled CPU, and hedge amplification.

## Design and operations checklist

- Define completeness, ranking, deduplication, and error semantics.
- Allocate one end-to-end deadline across queue, branch, and merge time.
- Bound fan-out globally and per dependency.
- Test skew, correlated failure, and cancellation leaks.

```text
latency = slowest required branch + merge
load = requests x fan-out x retries/hedges
```

## Test yourself

1. How would you budget a 200 ms deadline across 50 shards?
2. Which metric detects canceled work continuing remotely?
3. When can approximate top-k avoid full fan-out?

## Further reading

- Dean and Barroso, *The Tail at Scale*.
- Elasticsearch distributed search execution documentation.
- gRPC deadline and cancellation guides.
