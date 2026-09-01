# Stream-Processing Delivery Guarantees - Professional

> Exactly-once is a recovery protocol over state and externally visible effects,
> not a property conferred by an API flag.

## Named systems

**Apache Flink** implements distributed snapshots derived from Chandy-Lamport.
Barriers delimit input positions; aligned checkpoints pause faster inputs until
all barriers arrive, while unaligned checkpoints capture in-flight buffers.
`TwoPhaseCommittingSink` associates committables with checkpoint completion.
Failure recovery restores state and source positions, then resolves pending
commits through coordinator-managed committers.

**Kafka Streams EOS v2** uses Kafka transactions to atomically publish output
records, state-store changelog records, and consumed offsets. Tasks use
transactional producers and read-committed consumers. Producer epochs fence
zombie instances. The boundary is Kafka: an external HTTP or database effect is
not included merely because Kafka transactions are enabled.

**Spark Structured Streaming** records source offsets and batch commit metadata
in its checkpoint log. Deterministic replay reruns an incomplete micro-batch.
Exactly-once requires a replay-safe sink; `foreachBatch` exposes a batch ID that
can support deduplication, but user code must enforce it atomically.

## Scale and failure behavior

At 10x throughput, checkpoint I/O, transaction commit rate, and sink batching
become visible. At 100x state, snapshot duration and restore bandwidth dominate
recovery objectives. If a 20 TB state image restores at an effective 2 GB/s, raw
transfer alone takes nearly three hours before replay and warm-up.

Long outages accumulate pending Kafka transactions, staged object-store files,
or warehouse deduplication entries. Transaction timeouts shorter than checkpoint
plus recovery time can abort valid work; very long timeouts retain resources and
delay cleanup. Validate timeout inequalities under failure, not only steady state.

Exactly-once can still produce semantically wrong results when inputs lack stable
identities, user functions are nondeterministic, or external lookups change on
replay. Distinguish processing consistency from business correctness.

## Operations

Dashboard checkpoint completion and failure, alignment, snapshot bytes,
committable age, open/aborted transactions, recovery time, replay volume, sink
dedup hits, and source lag. Alert on the oldest pending commit, not only averages.

Runbook: stop new deployment churn; identify the last completed checkpoint;
inspect pending sink transactions or staged files; verify fencing; restore in a
staging namespace if commit status is ambiguous; reconcile by stable operation
ID rather than blindly replaying.

## Design and ops checklist

- State the guarantee separately for source, engine state, and every sink.
- Enumerate crash points before and after prepare, commit, and offset publication.
- Use stable operation identities and deterministic replay inputs.
- Ensure transaction and retention timeouts exceed worst-case recovery bounds.
- Test coordinator loss, zombie writers, ambiguous commits, and rollback.
- Capacity-plan checkpoint storage and restore bandwidth, not only throughput.
- Expose pending commit age and a safe reconciliation procedure.
- Document where the atomic boundary ends.

```text
DELIVERY CHEAT SHEET
checkpoint       source position + operator state
at-least-once    replay after failure; effects may repeat
2PC              prepare before checkpoint completion, commit after
idempotency      repeated stable operation has one effect
EOS boundary     ends wherever the transaction cannot reach
```

## Test yourself

1. Where does Kafka Streams EOS stop when a processor calls an external API?
2. How would you resolve a sink commit whose acknowledgement was lost?
3. Which timeout relationships must hold for checkpoint-bound transactions?
4. Why can deterministic recovery still produce semantically stale results?

## Further reading

- Chandy and Lamport, "Distributed Snapshots: Determining Global States."
- Carbone et al., "Lightweight Asynchronous Snapshots for Distributed Dataflows."
- Apache Flink checkpointing and sink API source/documentation.
- Kafka design documentation, transactions and exactly-once semantics.
- Spark Structured Streaming programming guide, fault tolerance semantics.
