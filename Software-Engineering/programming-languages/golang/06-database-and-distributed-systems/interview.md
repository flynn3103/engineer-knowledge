# Database and Distributed Systems — Interview Prep

> **Topic:** [Database and Distributed Systems](../README.md)

---

## Conceptual / Foundational

**Q: What is `sql.DB` actually?**
A: A connection pool, not a single connection — safe for concurrent use across goroutines. It should be created once at startup and reused, not opened per request.

**Q: What is idempotency, and why does it matter for retries?**
A: An operation is idempotent if running it multiple times produces the same result as running it once. It matters because a client can't reliably distinguish "my request never arrived," "it failed," and "it succeeded but the response was lost" after a timeout — retrying safely requires the operation to be idempotent.

**Q: Difference between optimistic and pessimistic locking?**
A: Optimistic locking uses a version/timestamp check with a conditional update and retries on conflict, holding no lock; pessimistic locking (`SELECT ... FOR UPDATE`) holds a row lock for the transaction's duration, guaranteeing no conflict but serializing access.

## Tricky / Trap Questions

**Q: A payment request times out client-side. Is it safe to retry?**
A: Only if the request carries an idempotency key that the server checks (via a unique constraint) before executing the side effect — otherwise the original request may have already succeeded, and retrying could create a duplicate charge.

**Q: Is a Redis `SETNX` + TTL lock safe for correctness-critical distributed coordination?**
A: Not by itself — if the lock holder is paused (GC, network partition) longer than the TTL, another process can acquire the "same" lock while the first still believes it holds it. Use a properly reviewed algorithm (Redlock) or a lease-based coordination service (etcd, ZooKeeper) when correctness genuinely depends on it.

**Q: Why is "update the cache on write" often worse than "invalidate the cache on write"?**
A: A slow write racing with a concurrent read-then-cache can leave the cache holding a stale value indefinitely if you update it directly. Deleting the entry on write and letting the next read repopulate it avoids this race.

## System / Design Scenarios

**Q: Design a queue consumer that processes messages exactly once, given the queue only guarantees at-least-once delivery.**
A: Persist a record of processed message IDs (with a unique constraint) inside the same transaction as the side effect; on redelivery, check the record first and skip (but still ack) if already processed.

**Q: Design a multi-step order-placement flow (reserve inventory, charge payment, create shipment) across three services without a distributed transaction.**
A: A saga: each step is a local transaction with a corresponding idempotent compensating action (release reservation, refund, cancel shipment); if a step fails, run compensations for prior steps in reverse order.

**Q: A service scales from 5 to 50 instances and the shared database starts rejecting connections. What happened, and how do you prevent it?**
A: `MaxOpenConns` per instance times instance count likely exceeded the database's max-connection limit. Prevent it by maintaining a documented, enforced per-service connection budget reviewed at every scale-up.

## Behavioral / Experience

**Q: Describe an incident involving a duplicate write or lost update, and what changed afterward.**
A: (Tailor to experience — strong answers describe adding an idempotency key, fixing a naive lock, or introducing a saga with compensations, with a measured before/after.)

---

## Cheat Sheet

```
sql.DB               → connection pool, create once, reuse
Idempotency key       → unique constraint, the only safe fix for retry ambiguity
At-least-once queues  → consumers must dedupe explicitly
Cache write path      → invalidate (delete), not update
Optimistic lock        → version + conditional update + retry on conflict
Pessimistic lock       → SELECT ... FOR UPDATE, held for the transaction
Saga                   → local txns + idempotent compensations, avoid distributed 2PC
Pool math              → MaxOpenConns * instances <= DB's real connection limit
```

---

## Related Topics

- [Junior](junior.md) · [Middle](middle.md) · [Senior](senior.md) · [Professional](professional.md) · [Tasks](tasks.md)
