# Database and Distributed Systems — Senior

> **Topic:** [Database and Distributed Systems](../README.md)
> **Focus:** Handling partial failures correctly (the two-phase problem), distributed locks, connection pool sizing under real load, saga-style compensation instead of distributed transactions, and designing for a downstream that's sometimes just gone.

---

## Introduction

At scale, "the database call failed" stops being a single failure mode. It might mean the write never reached the database, or it reached the database and committed but the response was lost on the way back, or it's still in flight and you genuinely don't know. Senior-level distributed-systems work is designing systems that behave correctly under this ambiguity, not just under the happy path.

---

## Prerequisites

- Comfortable with idempotency keys, queue consumers, and optimistic/pessimistic locking (middle level).

---

## Core Concepts

### 1. The fundamental partial-failure problem

When a client calls a service and gets a timeout or connection error, there are exactly three possibilities: the operation never started, it started and failed, or it started and **succeeded** but the response never made it back. Without an idempotency key, the client cannot safely distinguish these — retrying might duplicate a successful operation, and not retrying might silently drop a failed one. This is why idempotency (middle level) isn't a nice-to-have at scale — it's the only way to make retries safe under genuine ambiguity.

### 2. Distributed locks are a coordination tool, not a correctness guarantee by default

```go
acquired, err := redisClient.SetNX(ctx, lockKey, ownerID, 30*time.Second).Result()
if !acquired {
    return ErrLockHeld
}
defer redisClient.Del(ctx, lockKey) // only if we still own it — see caveat below
```

A naive Redis-based lock (`SETNX` + TTL) has a well-known failure mode: if the holder is paused (GC, network partition) longer than the TTL, another process can acquire the "same" lock while the first still believes it holds it — both then proceed concurrently. Production-grade distributed locking (e.g. the Redlock algorithm, or better, a strongly consistent coordination service like etcd/ZooKeeper with lease-based locks) is required if correctness genuinely depends on mutual exclusion across processes, not just "usually fine."

### 3. Avoid distributed transactions; use sagas with compensation instead

A two-phase-commit-style distributed transaction across multiple services is operationally expensive and fragile (a coordinator failure can leave participants blocked indefinitely). The more common, more resilient pattern is a **saga**: a sequence of local transactions, each with a corresponding **compensating action** to undo it if a later step fails.

```
1. Reserve inventory        (compensate: release reservation)
2. Charge payment           (compensate: refund)
3. Create shipment          (compensate: cancel shipment)
```

If step 3 fails, run compensations for steps 2 and 1, in reverse order. Each step and compensation should itself be idempotent, since the saga orchestrator may retry a step or its compensation after a crash.

### 4. Connection pool sizing needs to account for the database's own limits

`db.SetMaxOpenConns(N)` per service instance, multiplied by the number of running instances, must stay under the database's actual max-connection limit — a routine horizontal scale-up (more pods/instances) without revisiting this math is a common, entirely self-inflicted way to exhaust a database's connection limit during a traffic spike.

### 5. Design for "the downstream is just gone"

A downstream that's slow is a timeout problem (Topic 05). A downstream that's **completely unreachable for an extended period** (a multi-hour outage, a network partition) requires a different design question: can the operation be queued and retried later (asynchronous, degraded-but-available), or must it fail immediately and visibly? Designing this decision explicitly, per operation, before an outage happens, is far better than discovering the answer live during one.

---

## Worked Example — A Duplicate Charge From an Ambiguous Timeout

A payment service call timed out client-side after 5 seconds; the client, having no idempotency key, retried. The original request had actually succeeded server-side just after the client gave up — the retry created a second charge. The fix: every payment-initiating call now requires a client-generated idempotency key, persisted with a unique constraint before any external payment provider is called, so a retry with the same key is detected and returns the original result instead of re-executing the charge.

---

## Pros & Cons

| Approach | Pros | Cons |
|---|---|---|
| Idempotency keys under ambiguous failures | The only reliable way to make retries safe | Requires the key to be generated and reused correctly by the *caller*, which you don't fully control |
| Redis-based lock (`SETNX` + TTL) | Simple, fast | Not safe against process pauses exceeding the TTL — use a proper algorithm/service if correctness depends on it |
| Sagas with compensation | Avoids fragile distributed transactions, resilient to partial failure | Requires designing and testing a compensating action for every step |

---

## Best Practices

1. Treat every write across a network boundary as potentially ambiguous on failure; require an idempotency key.
2. Don't roll your own distributed lock for correctness-critical coordination — use a well-reviewed algorithm or a coordination service, and understand its failure modes.
3. Prefer sagas with compensating actions over distributed transactions across services.
4. Recompute total connection-pool capacity against the database's actual limit whenever scaling instance count.
5. Explicitly decide, per operation, the behavior when a downstream is unreachable for an extended period — queue-and-retry vs. fail-fast-and-visible.

---

## Edge Cases & Pitfalls

- **A compensating action that isn't itself idempotent** can double-refund or double-cancel if the saga orchestrator retries it after a crash — compensations need the same rigor as the original steps.
- **A distributed lock's TTL set too short** for the actual work duration causes the lock to expire mid-operation, allowing a second holder in — size the TTL generously and consider lease renewal for long operations.
- **Connection pool exhaustion from an uncoordinated scale-up** is a self-inflicted outage that looks, from symptoms alone, exactly like a database performance problem.

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| Retrying a network-ambiguous write without an idempotency key | Always require one for writes that cross a network boundary and can be retried |
| Rolling a naive Redis lock for genuinely correctness-critical coordination | Use Redlock properly, or a lease-based coordination service |
| Attempting a distributed transaction across service boundaries | Use a saga with compensating actions instead |
| Scaling instance count without revisiting `MaxOpenConns * instances` against the DB's limit | Recalculate and adjust per-instance pool size on every scaling change |

---

## Cheat Sheet

```
Partial failure  → 3 possibilities on timeout: never started / failed / succeeded-but-lost-response
Idempotency key  → the only safe way to retry under that ambiguity
Distributed lock → SETNX+TTL is NOT safe against long pauses; use Redlock/etcd/ZK properly
Saga             → sequence of local txns + compensating actions, avoid distributed 2PC
Pool math        → MaxOpenConns * instance_count <= DB's actual max connections
```

---

## Summary

- A network-boundary write's failure is fundamentally ambiguous (never started / failed / succeeded-but-lost) — idempotency keys are the only reliable fix, not a nice-to-have.
- Naive distributed locks (`SETNX` + TTL) are not safe against process pauses exceeding the TTL; use a properly reviewed algorithm or coordination service when correctness genuinely depends on mutual exclusion.
- Prefer sagas with idempotent compensating actions over distributed transactions across services.
- Recalculate total connection-pool capacity against the database's real limit on every scale-up.
- Decide explicitly, per operation, how to behave when a downstream is unreachable for an extended period.

---

## Further Reading

- Martin Kleppmann — *How to do distributed locking* (critique of naive Redis locks): <https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html>
- Chris Richardson — *Pattern: Saga*: <https://microservices.io/patterns/data/saga.html>

---

## Related Topics

- [HTTP and APIs — Senior](../05-http-and-apis/senior.md) — circuit breakers and deadline propagation for the same failure modes.
- [Production Debugging — Senior](../07-production-debugging/senior.md)

---

## Check your understanding

1. Explain Database and Distributed Systems — Senior Level in your own words and name the problem it solves.
2. How would you apply the ideas around Introduction, Prerequisites, Core Concepts in a realistic engineering change?
3. What failure mode or misuse should you look for, and what evidence would reveal it?
4. How would you validate a system-level decision about Database and Distributed Systems — Senior Level under uncertainty?
5. What observable result would convince you that the approach improved the system?
