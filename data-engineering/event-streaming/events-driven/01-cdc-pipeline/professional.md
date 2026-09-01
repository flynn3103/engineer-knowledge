# CDC Pipeline - Professional
PostgreSQL logical decoding reads WAL through replication slots; Debezium stores source offsets and snapshot state through Kafka Connect. Kafka partitions preserve key-local order, not global transaction order.
At 10x load, serialization and broker throughput dominate; at 100x, retained WAL and recovery time become existential. Dashboard commit-to-Kafka lag, confirmed LSN, retained WAL bytes, snapshot rate, schema errors, and sink convergence.
## Best practices
- Set disk-based WAL retention guardrails and an emergency slot policy.
- Make sinks version-aware and replayable.
- Rehearse schema changes and connector upgrades.
- Capacity-test snapshot plus live churn together.
```text
snapshot establishes state; WAL preserves change order
offset progress without sink convergence is not correctness
```
## Test yourself
1. How would you prevent a slot from exhausting disk during Kafka outage?
2. What contract preserves cross-table transaction meaning?
3. When is Outbox preferable to log-based CDC?
## Further reading
- PostgreSQL Logical Decoding and Replication Slots documentation.
- Debezium PostgreSQL connector documentation and source.
- Kafka Connect offset storage design.
