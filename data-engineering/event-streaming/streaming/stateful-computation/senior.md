# Stateful Computation - Senior

> How do you keep correct state from becoming an unbounded operational burden?

| Risk | Failure | Control |
|---|---|---|
| No retention | checkpoint and disk grow forever | semantic TTL or window cleanup |
| Hot key | one state shard saturates | split associative work or isolate tenant |
| Large values | serialization and write amplification | incremental structures and compaction |
| Schema change | restore/deserialization fails | versioned serializer migration |
| Rescale | network and restore exceed SLO | key-group planning and incremental snapshots |

TTL is part of correctness. A deduplication key retained for one hour allows a
duplicate after one hour; a customer balance cannot expire merely to save disk.
Choose retention from business replay and lateness horizons, then measure its
state cost.

State schema upgrades require restore tests against real savepoints. Adding a
field may be compatible in Avro while changing a custom key serializer can make
old state unreachable. Preserve stable operator IDs and rollback binaries.

Use asynchronous state access only when ordering semantics remain explicit. It
can hide storage latency, but concurrent operations for the same key must not
reorder updates that depend on previous state.

## Test yourself

1. Why is deduplication TTL a correctness decision?
2. What makes a state serializer change riskier than an event schema change?
3. How would you detect and mitigate one hot state key?

Continue to [`professional.md`](professional.md).
