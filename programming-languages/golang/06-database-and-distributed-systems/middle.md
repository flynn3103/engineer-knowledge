# Database and Distributed Systems — Middle

> **Topic:** [Database and Distributed Systems](../README.md)
> **Focus:** Idempotency keys in practice, message queues (producer/consumer patterns), caching strategies and invalidation, rate limiting, and optimistic vs. pessimistic locking.

---

## Introduction

At junior level you learned the mechanics of `database/sql`, transactions, and the *idea* of idempotency. At this level you build the actual patterns: idempotency keys that survive real retries, a queue consumer that doesn't lose or duplicate work, a cache that doesn't serve stale data forever, and locking strategies for concurrent updates to the same row.

---

## Prerequisites

- Comfortable with transactions, connection pooling, and parameterized queries (junior level).

---

## Core Concepts

### 1. Idempotency keys, end to end

```go
func chargeCard(ctx context.Context, db *sql.DB, idempotencyKey, userID string, amount int) error {
    _, err := db.ExecContext(ctx,
        `INSERT INTO charges (idempotency_key, user_id, amount, status)
         VALUES ($1, $2, $3, 'pending')
         ON CONFLICT (idempotency_key) DO NOTHING`,
        idempotencyKey, userID, amount)
    if err != nil { return err }
    // proceed to actually charge, using idempotencyKey as the record of "have we done this"
    return processCharge(ctx, db, idempotencyKey)
}
```

The caller supplies a unique key (often a UUID generated once per logical operation, reused across retries of *that same* operation). The server uses a unique constraint to guarantee the insert — and therefore the side effect — happens at most once, regardless of how many times the request is retried.

### 2. Queue consumers: at-least-once delivery is the default assumption

Most message queues (SQS, Kafka, RabbitMQ) guarantee **at-least-once** delivery, not exactly-once — a consumer must assume any message might be redelivered (after a crash, a timeout, a redeploy) and handle it idempotently, the same way an HTTP retry must be handled idempotently.

```go
func consume(ctx context.Context, msg Message) error {
    if alreadyProcessed(msg.ID) { // check idempotency record
        return ackMessage(msg)
    }
    if err := process(msg); err != nil {
        return err // don't ack — let it redeliver
    }
    markProcessed(msg.ID)
    return ackMessage(msg)
}
```

### 3. Cache invalidation: pick a strategy deliberately

- **TTL-based**: simplest, accepts staleness up to the TTL window.
- **Write-through**: update cache and database together, on the write path.
- **Cache-aside (lazy loading)**: read populates the cache on a miss; writes invalidate (don't update) the cache entry, letting the next read repopulate it.

```go
func getUser(ctx context.Context, id string) (User, error) {
    if u, ok := cache.Get(id); ok {
        return u, nil
    }
    u, err := db.GetUser(ctx, id)
    if err != nil { return User{}, err }
    cache.Set(id, u, 5*time.Minute)
    return u, nil
}
func updateUser(ctx context.Context, u User) error {
    if err := db.UpdateUser(ctx, u); err != nil { return err }
    cache.Delete(u.ID) // invalidate, don't try to update the cache directly
    return nil
}
```

Invalidating (deleting) on write, rather than updating the cache entry directly, avoids race conditions where a slow write and a concurrent read-then-cache could leave the cache holding stale data indefinitely.

### 4. Rate limiting protects both sides

```go
limiter := rate.NewLimiter(rate.Limit(100), 20) // 100/sec, burst 20
if !limiter.Allow() {
    return ErrRateLimited
}
```

`golang.org/x/time/rate`'s token-bucket limiter is the standard building block — `Limit` is the steady-state rate, the burst size allows short spikes above it. Rate limiting protects your own service from being overwhelmed by a caller, and (when you're the caller) protects a downstream dependency from being overwhelmed by you.

### 5. Optimistic vs. pessimistic locking

```go
// Optimistic: version column, no lock held
res, err := db.ExecContext(ctx,
    "UPDATE items SET stock = stock - 1, version = version + 1 WHERE id = $1 AND version = $2",
    id, expectedVersion)
if n, _ := res.RowsAffected(); n == 0 {
    return ErrConflict // someone else updated it first — retry or fail
}

// Pessimistic: row lock held for the transaction's duration
tx.QueryRowContext(ctx, "SELECT stock FROM items WHERE id = $1 FOR UPDATE", id)
```

Optimistic locking (a version/timestamp check) scales better under low contention — no lock held, but a conflict requires the caller to retry. Pessimistic locking (`SELECT ... FOR UPDATE`) guarantees no conflict but serializes access to that row for the duration of the transaction, which can become a bottleneck under high contention on the same rows.

---

## Code Examples

### Example 1 — A queue consumer with idempotent processing

```go
type ProcessedRecord struct{}

func handleMessage(ctx context.Context, db *sql.DB, msg Message) error {
    tx, err := db.BeginTx(ctx, nil)
    if err != nil { return err }
    defer tx.Rollback()

    res, err := tx.ExecContext(ctx,
        "INSERT INTO processed_messages (id) VALUES ($1) ON CONFLICT DO NOTHING", msg.ID)
    if err != nil { return err }
    if n, _ := res.RowsAffected(); n == 0 {
        return tx.Commit() // already processed; ack without redoing side effects
    }
    if err := applySideEffect(ctx, tx, msg); err != nil { return err }
    return tx.Commit()
}
```

### Example 2 — Optimistic-locking retry loop

```go
for attempt := 0; attempt < 3; attempt++ {
    item, _ := getItem(ctx, db, id)
    ok, err := tryUpdate(ctx, db, item)
    if err != nil { return err }
    if ok { return nil }
    // conflict — reload and retry
}
return ErrTooManyConflicts
```

---

## Pros & Cons

| Approach | Pros | Cons |
|---|---|---|
| Idempotency keys | Safe retries, no duplicate side effects | Requires a persisted record and unique constraint per operation |
| Cache-aside with invalidation | Simple, avoids serving updates twice | A brief window of cache-miss traffic hits the DB right after invalidation |
| Optimistic locking | No lock held, scales under low contention | Requires retry logic on conflict; can starve under high contention |
| Pessimistic locking | No caller-side retry needed | Serializes access, can bottleneck under high contention |

---

## Best Practices

1. Require an idempotency key on any client-retriable write endpoint, backed by a unique constraint.
2. Assume at-least-once delivery for any queue consumer; make processing idempotent, not "probably fine."
3. Invalidate (don't update) cache entries on write to avoid stale-write races.
4. Rate-limit both inbound (protect yourself) and outbound (protect downstreams) traffic.
5. Default to optimistic locking unless contention is measured to be high enough to justify pessimistic locks.

---

## Edge Cases & Pitfalls

- **An idempotency key reused across genuinely different logical operations** (e.g. a client bug reusing the same UUID) silently drops the second, different operation — validate the key's scope matches the intended operation.
- **A cache invalidation that fails silently** (network blip to the cache) leaves stale data indefinitely until the next unrelated write — consider a short TTL as a backstop even with invalidation.
- **Optimistic locking without a retry limit** can loop indefinitely under sustained high contention — always cap attempts.

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| No idempotency key on a retriable write endpoint | Require one, enforced by a unique constraint |
| Treating queue delivery as exactly-once | Design consumers to be idempotent |
| Updating (not invalidating) a cache entry on write | Delete on write, let the next read repopulate |
| Pessimistic locking by default everywhere | Reserve it for genuinely high-contention paths; default to optimistic |

---

## Tricky Points

- A `SELECT ... FOR UPDATE` lock is held for the remainder of the transaction, not just the statement — a slow subsequent statement in the same transaction extends the lock's duration.
- Cache invalidation and the database write are not atomic by default — a crash between the two can leave a stale cache entry; a short TTL as a backstop mitigates this.

---

## Cheat Sheet

```
Idempotency key   → unique constraint + ON CONFLICT DO NOTHING
Queue consumer    → assume at-least-once, dedupe by message ID
Cache write path  → invalidate (delete), don't update directly
Rate limiter      → token bucket, x/time/rate
Optimistic lock   → version column + conditional UPDATE + retry on 0 rows affected
Pessimistic lock  → SELECT ... FOR UPDATE, held for the transaction
```

---

## Summary

- Idempotency keys with a unique constraint make retried writes safe by design.
- Queue consumers should assume at-least-once delivery and dedupe explicitly.
- Cache-aside with invalidation-on-write (not update-on-write) avoids stale-data races.
- Rate limiting protects both your own service and the downstreams you call.
- Optimistic locking scales better under low contention; pessimistic locking avoids caller-side retries at the cost of serializing access.

---

## Further Reading

- Stripe — *Idempotent Requests* (API design reference, patterns transfer): <https://stripe.com/docs/api/idempotent_requests>
- `golang.org/x/time/rate`: <https://pkg.go.dev/golang.org/x/time/rate>

---

## Related Topics

- [Database and Distributed Systems — Junior](junior.md)
- [HTTP and APIs — Middle](../05-http-and-apis/middle.md) — idempotency from the client-retry side.

---

## Check your understanding

1. Explain Database and Distributed Systems — Middle Level in your own words and name the problem it solves.
2. How would you apply the ideas around Introduction, Prerequisites, Core Concepts in a realistic engineering change?
3. What failure mode or misuse should you look for, and what evidence would reveal it?
4. Which local design trade-off would make you choose or reject Database and Distributed Systems — Middle Level in an existing codebase?
5. What observable result would convince you that the approach improved the system?
