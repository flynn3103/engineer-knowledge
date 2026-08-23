# Database and Distributed Systems — Hands-On Tasks

> **Topic:** [Database and Distributed Systems](../README.md)

---

## Warm-Up

1. Set up a `sql.DB` against a local SQLite or Postgres instance, configure `SetMaxOpenConns`/`SetConnMaxLifetime`, and write a query that scans into a struct, correctly handling `sql.ErrNoRows`.
2. Write a transactional funds-transfer function (debit one account, credit another) using `defer tx.Rollback()`, and write a test that forces a failure mid-transfer to confirm the debit is rolled back.
3. Demonstrate a SQL injection vulnerability with string-concatenated SQL against a test database, then fix it with a parameterized query.

## Core

4. Implement an idempotency-key-protected "create order" endpoint: a unique constraint on the key, returning the original result on a duplicate key instead of creating a second order. Test it by calling the endpoint twice with the same key.
5. Build a simple in-memory queue consumer that simulates at-least-once delivery (redeliver ~10% of messages randomly) and implement idempotent processing using a "processed IDs" table, verifying no side effect runs twice despite redeliveries.
6. Implement cache-aside reads with invalidate-on-write for a simple key-value store backed by a map (standing in for a real cache) and a database; write a test proving a write followed immediately by a read never returns stale data.

## Advanced

7. Implement optimistic locking for a "decrement stock" operation (version column + conditional update), and write a concurrent test (multiple goroutines decrementing simultaneously) proving no overselling occurs, with a bounded retry loop on conflict.
8. Implement a basic distributed lock using a database's unique constraint (or a simulated Redis `SETNX`), and write a test demonstrating the "TTL expires while holder is still working" failure mode — then discuss (in writing) how a lease-renewal mechanism would fix it.
9. Design and implement a 3-step saga (in-memory, simulating 3 services) with compensating actions for each step; write a test where step 3 fails and verify steps 1 and 2's compensations run in reverse order, restoring the system to a consistent state.

## Capstone

10. Build a small "wallet" service combining everything: idempotency-key-protected credit/debit endpoints backed by a unique constraint, optimistic-locking balance updates, a queue consumer applying transactions with idempotent processing, and cache-aside balance reads with invalidate-on-write. Write a test suite covering: duplicate requests (idempotency), concurrent debits (optimistic locking), and redelivered queue messages (dedup).

## If you can do all of these, you have the middle level

You can design write paths that are safe under retries and redeliveries, choose correctly between optimistic and pessimistic locking, and reason about compensations instead of reaching for a distributed transaction.

---

## Related Topics

- [Junior](junior.md) · [Middle](middle.md) · [Senior](senior.md) · [Professional](professional.md) · [Interview](interview.md)
