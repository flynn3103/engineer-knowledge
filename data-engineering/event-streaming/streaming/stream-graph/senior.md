# Stream Graph - Senior

> How do you evolve and rescale a graph without losing state or moving the
> bottleneck somewhere less visible?

The middle-level graph still fails under skew. Hash partitioning balances keys,
not work: one tenant producing 30% of records pins 30% of work and state to one
subtask while peers remain idle.

| Failure mode | Evidence | Design response |
|---|---|---|
| Hot key | one busy subtask, high per-key rate | split combinable work, two-stage aggregate |
| Hidden shuffle | network and serialization dominate | chain or repartition once deliberately |
| Sink bottleneck | upstream backpressure, sink busy | batch writes, increase safe sink parallelism |
| State-heavy rescale | long restore and rebalance | incremental snapshots, planned key groups |
| Topology change | restore rejects old state | stable operator IDs and compatible serializers |

Flink assigns keyed state to **key groups**, with `maxParallelism` fixing the
number of groups. Rescaling redistributes groups rather than individual keys.
Choosing an excessively small `maxParallelism` constrains future scale;
changing it later can require state migration.

Give stateful operators stable UIDs. Generated IDs can change when a harmless
operator is inserted, leaving a savepoint unable to map old state to the new
graph. Treat state schema and serializer compatibility like a database schema
migration: stage it, test restore, and preserve rollback artifacts.

For skewed additive aggregates, salt a hot logical key into bounded subkeys,
aggregate locally, then merge. This adds a shuffle and state but removes one
serial bottleneck. It is unsafe for non-associative operations without a
correct merge function.

## Test yourself

1. Why does balanced key count not imply balanced work?
2. What role does Flink `maxParallelism` play during rescaling?
3. How would you deploy a topology change while preserving rollback?

Continue to [`professional.md`](professional.md).
