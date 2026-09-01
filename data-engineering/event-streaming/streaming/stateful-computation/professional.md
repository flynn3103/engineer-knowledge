# Stateful Computation - Professional

> Managed state is a distributed database embedded in the execution engine, with
> ownership, storage, snapshot, compaction, migration, and recovery concerns.

## Named implementations

**Apache Flink** partitions keyed state into key groups. Heap backends hold
objects in JVM memory and snapshot serialized state. The EmbeddedRocksDB backend
stores state in RocksDB LSM trees and supports incremental checkpoints by reusing
immutable SST files. This lowers checkpoint upload volume but introduces
serialization, block-cache, compaction, and local-disk behavior. ForStStateBackend
targets disaggregated remote storage and asynchronous state access.

**Kafka Streams** uses local state stores, commonly RocksDB, backed by replicated
Kafka changelog topics. A task restores by replaying its changelog. Standby and
warmup replicas trade additional storage/network traffic for lower rebalance
downtime. RocksDB block cache, memtables, compaction, and changelog restore rate
jointly determine recovery.

**Apache Samza** similarly combines partition-affine local stores with changelog
streams. Its model makes the log the durable recovery source and local state a
materialized acceleration, illustrating the general log-plus-index architecture.

## Scale and failure behavior

At 10x keys, metadata and per-entry overhead can exceed payload bytes. At 100x
updates, LSM compaction and write amplification consume disk bandwidth while
checkpoints compete for I/O. A 5 TB shard restoring at 200 MB/s needs about seven
hours before replay; recovery bandwidth must be a first-class capacity target.

Incremental snapshots reduce transferred bytes only when SST reuse is high.
Heavy updates and compaction invalidate files, causing checkpoint size spikes.
Rescaling can move terabytes and invalidate warm caches, producing a long tail
after the nominal restore completes.

## Operations

Dashboard logical and physical state bytes, keys and timers, snapshot delta/full
size, checkpoint upload time, restore bytes/rate, RocksDB compaction pending
bytes, write stalls, block-cache hit rate, local disk, changelog lag, and skew by
task.

Runbook for state growth: identify operator and key namespace; separate expected
cardinality from missing cleanup; inspect TTL semantics and timer cleanup; sample
large keys; estimate checkpoint/restore impact before deleting or migrating
state; preserve a savepoint for rollback.

## Design and ops checklist

- Define state lifetime from semantics and recovery horizons.
- Estimate payload plus key, timer, index, and storage-engine overhead.
- Choose heap, embedded disk, or remote state from latency and recovery needs.
- Version state names and serializers; test forward and rollback restore.
- Capacity-plan compaction, checkpoint, and restore I/O concurrently.
- Bound per-key state and detect skew before fleet averages hide it.
- Test rescaling and cold-cache recovery with production-sized snapshots.
- Document authoritative recovery source and data-loss boundary.

```text
STATE CHEAT SHEET
key group       unit of Flink keyed-state assignment
RocksDB         local LSM index; compaction and cache matter
changelog       ordered mutations used to rebuild local stores
incremental CP  reuses immutable files; update churn reduces reuse
TTL             semantic expiration plus storage cleanup policy
```

## Test yourself

1. Why can incremental checkpoint size spike after compaction?
2. How would you set a recovery SLO for a multi-terabyte state shard?
3. When are standby replicas worth their ongoing cost?
4. Which metrics distinguish missing TTL cleanup from LSM write amplification?

## Further reading

- Apache Flink documentation and source for keyed state and state backends.
- Apache Kafka Streams architecture and state-store restoration documentation.
- RocksDB Wiki, compaction and block cache internals.
- Noghabi et al., "Samza: Stateful Scalable Stream Processing at LinkedIn."
- Carbone et al., "State Management in Apache Flink."
