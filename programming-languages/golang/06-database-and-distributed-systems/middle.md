# Database and Distributed Systems — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Database and Distributed Systems** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
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

## Apply it

1. Find a real component where **Database and Distributed Systems** affects an interface or dependency.
2. Write two plausible choices and the constraint that favors each one.
3. Make the smallest reversible change at that boundary.
4. Exercise the component alone, then exercise the integrated flow.
5. Keep the decision note with the evidence that selected the option.

## Verify your work

- A focused check proves the local behavior.
- An integrated check proves callers and dependencies still agree.
- Logs, traces, compiler output, or benchmarks expose the boundary.
- Reverting the change restores the previous behavior without unrelated edits.

## Review questions

- Which boundary is most affected by Database and Distributed Systems?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
