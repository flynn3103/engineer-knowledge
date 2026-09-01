# Two-Phase and Three-Phase Commit - Professional

Atomic commit is consensus on a constrained outcome, with durability ordering and uncertain failure detection.

## Real systems

- PostgreSQL stores two-phase state in WAL and `pg_twophase`; `max_prepared_transactions` bounds it.
- XA coordinates resource managers using XIDs and a transaction manager log.
- Spanner combines Paxos-replicated data with 2PC across participant groups.
- CockroachDB uses transaction records and parallel commits rather than classic external 2PC.

At scale, lock duration and slowest-participant latency dominate. Dashboard in-doubt age, participants per transaction, coordinator-log fsync, abort ratio, and recovery backlog.

## Design and operations checklist

- Prove fsync-before-act ordering.
- Replicate or recover the authoritative decision.
- Bound participant count and pre-prepare work.
- Provide inspected resolution, never guess silently.

```text
prepare = durable promise
decision = durable global truth
```

## Test yourself

1. Why does replicated coordination not remove participant blocking?
2. What evidence permits manual commit of an in-doubt XID?
3. How do consensus groups change the failure model?

## Further reading

- Gray and Lamport, *Consensus on Transaction Commit*.
- PostgreSQL Two-Phase Transactions documentation and source.
- Spanner paper.
