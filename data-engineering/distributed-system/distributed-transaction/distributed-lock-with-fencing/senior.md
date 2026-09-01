# Distributed Locks with Fencing - Senior

Fencing protects writes only when every mutation passes through a resource that compares tokens.

| Failure | Unsafe result | Required control |
|---|---|---|
| holder pauses past TTL | stale write | resource-enforced fencing |
| release arrives late | deletes new owner's lock | owner-checked release |
| lock store loses counter state | reused token | durable monotonic issuer |
| hot lock | queueing and timeouts | partition work or use fair leases |
| resource cannot compare tokens | corruption remains possible | redesign commit boundary |

Measure acquisition p99, lease losses, stale-write rejections, renewal failures, and fairness. Chaos-test pauses longer than TTL, partitions, lock-store failover, and delayed writes. For Iceberg/Delta maintenance, prefer optimistic metadata commits when the storage system already supplies compare-and-swap semantics.

## Test yourself

1. When does fencing fail to protect a resource?
2. Which metric proves stale holders are occurring?
3. When is optimistic concurrency better than a distributed lock?

Continue to [`professional.md`](professional.md).
