# Stream-Processing Delivery Guarantees - Senior

> How do you carry checkpoint consistency through a sink outside the stream
> processor?

| Sink strategy | Strength | Main cost or risk |
|---|---|---|
| Two-phase commit | Atomic checkpoint-bound visibility | open transactions and coordinator coupling |
| Idempotent upsert | Replay produces same final value | requires stable business/result key |
| Deduplication ledger | Handles non-idempotent effects | storage, retention, atomicity |
| At-least-once append | Simple and durable | downstream must reconcile duplicates |

Flink's two-phase-commit sink begins a transaction, writes records, precommits on
a checkpoint barrier, and commits only after the coordinator declares the
checkpoint complete. Recovery aborts or resolves transactions associated with
incomplete checkpoints.

For an Iceberg sink, committed snapshots and checkpoint metadata must map
deterministically so replay does not publish duplicate data files. For warehouse
upserts, key results by `(job, partition, window_end)` and make the mutation
atomic. A read-then-insert dedup check is still racy.

Checkpoint intervals trade recovery work against overhead and transaction age.
Long intervals replay more data and keep sink transactions open longer. Short
intervals increase snapshot, metadata, and commit load.

## Test yourself

1. When is an idempotent upsert simpler than two-phase commit?
2. Why must deduplication and the business effect be atomic?
3. How does checkpoint interval affect sink transaction age?

Continue to [`professional.md`](professional.md).
