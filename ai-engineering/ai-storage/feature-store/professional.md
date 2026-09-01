# Feature Store - Professional

A feature store is a temporal data platform with two serving planes: bulk,
historically correct retrieval and low-latency current-value lookup. Its hard
problems are semantics, consistency, lineage, backfills, and ownership rather
than the key-value API.

## Real-system internals

**Feast** separates a registry and feature definitions from offline/online
stores. Historical retrieval performs point-in-time joins; materialization
moves a bounded time range into an online store. Feast intentionally delegates
feature transformation orchestration to surrounding compute systems in many
deployments.

**Apache Flink** supports event-time stream computation with watermarks,
stateful operators, checkpoints, and exactly-once state consistency. A feature
pipeline still needs idempotent external sinks and an explicit late-event
policy; checkpoint consistency does not make arbitrary side effects atomic.

**Apache Iceberg** provides snapshot isolation, schema/partition evolution,
time travel, and metadata for offline feature tables. Snapshot IDs make
training inputs reproducible, while compaction and snapshot expiration require
coordination with retained model/dataset lineage.

**Redis or DynamoDB** commonly provide online key lookup. TTL, eviction,
replication lag, hot keys, item-size limits, and multi-key atomicity determine
whether a logical feature group is actually fresh and consistent.

## Scale and correctness

At 10x, point-in-time joins and backfills consume warehouse/lakehouse compute;
partition by event date and entity distribution, prune early, and isolate
interactive workloads. At 100x, online fan-out, hot partitions, materialization
write amplification, and registry/lineage cardinality dominate.

Use a durable feature-value identity such as `(entity, feature_view_version,
event_time)` and idempotent materialization. Publish a generation/version
marker only after all values in an atomic feature group are available. Clients
can reject a mixed generation rather than silently combining incompatible data.

## Governance and operations

The registry should expose owner, description, entity, schema, transformation,
source lineage, freshness expectation, privacy class, allowed consumers,
deprecation state, and validated model dependencies. Feature discovery without
ownership creates reuse of misunderstood data.

Dashboard historical-join duration/skew, source and materialization lag,
online p50/p95/p99, hit/missing/stale rates, default use, version mix, hot keys,
quality violations, backfill progress, and offline-online parity samples.

A postmortem should identify the first incorrect layer: source event,
transformation, temporal join, offline snapshot, materialization, online store,
client fallback, or model interpretation. "Bad feature" is not a root cause.

## Design and operations checklist

- [ ] Feature semantics, event time, ownership, and versioning are explicit.
- [ ] Historical retrieval is tested against leakage and late-data fixtures.
- [ ] Offline snapshots and transformation artifacts reproduce training data.
- [ ] Materialization is idempotent, checkpointed, and generation-consistent.
- [ ] Online SLOs cover freshness and correctness, not latency alone.
- [ ] Backfills cannot starve production serving or silently mix versions.
- [ ] Lineage, privacy, access, deprecation, and model dependencies are queryable.

## Cheat sheet

```text
entity             = semantic subject and lookup key
feature definition = transformation + schema + time semantics + owner + version
offline store      = historical values for training and batch inference
online store       = latest values for low-latency prediction
point-in-time join = newest available feature value not later than prediction time
materialization    = publish computed feature values to online serving
```

## Test yourself

1. Design generation-consistent publication for ten features stored across keys.
2. How would you reproduce a training dataset after Iceberg snapshots expire?
3. Which signals distinguish stale computation from online-store replication lag?

## Further reading

- Feast source and documentation on historical retrieval and materialization
- Apache Flink documentation on event time, watermarks, and checkpointing
- Apache Iceberg specification and snapshot-management documentation
- Uber Engineering, "Michelangelo: Uber's Machine Learning Platform"
- Google Cloud, "Feast: an open source feature store for machine learning"
