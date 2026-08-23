# Database and Distributed Systems — Junior Level

> **Topic:** [Database and Distributed Systems](../README.md)
> **Focus:** `database/sql` basics, connection pooling, transactions, and the first idea of idempotency — writing data access code that doesn't silently corrupt state.

---

## Introduction

Go talks to databases through the standard `database/sql` package plus a driver (`lib/pq`, `pgx`, `go-sql-driver/mysql`, etc.). `database/sql` already manages a **connection pool** for you — you don't open and close a raw connection per query, you borrow one from the pool and return it. Understanding that pool, transactions, and the basic idea of "what happens if this runs twice" is the foundation everything else in this topic builds on.

---

## Prerequisites

- Comfortable with `error` handling and basic struct usage.
- No prior SQL/database-driver experience assumed beyond basic SQL syntax.

---

## Glossary

| Term | Definition |
|------|-----------|
| **`sql.DB`** | Not a single connection — a pool of connections, safe for concurrent use across goroutines. |
| **Connection pool** | A managed set of open connections, reused across queries instead of opened/closed per call. |
| **Transaction (`sql.Tx`)** | A group of statements executed atomically — all succeed or all roll back. |
| **`Commit`** | Finalizes a transaction's changes. |
| **`Rollback`** | Discards a transaction's changes. |
| **Idempotency** | An operation that produces the same end state whether run once or multiple times. |
| **Queue** | An ordered channel for decoupling producers from consumers, often across process/service boundaries. |
| **Cache** | A fast, usually in-memory or near-memory, store of recently or frequently accessed data. |
| **Rate limit** | A cap on how many operations are allowed in a given time window. |
| **Lock** | A mechanism ensuring only one actor at a time can modify a piece of shared state. |

---

## Core Concepts

### 1. `sql.DB` is a pool, not a connection

```go
db, err := sql.Open("postgres", dsn)
// db.Open does NOT immediately connect — it's lazy
db.SetMaxOpenConns(25)
db.SetMaxIdleConns(25)
db.SetConnMaxLifetime(5 * time.Minute)
```

Call `sql.Open` **once** at startup and reuse the same `*sql.DB` for the life of the program — never open a new one per request. It already handles concurrent access safely and manages a pool of underlying connections.

### 2. Always check `Ping` or the first query, not just `Open`

```go
db, err := sql.Open("postgres", dsn)
if err != nil { return err }
if err := db.Ping(); err != nil {
    return fmt.Errorf("db unreachable: %w", err)
}
```

`sql.Open` validates arguments but doesn't establish a connection — a typo'd DSN won't fail until the first real query unless you `Ping` explicitly.

### 3. Transactions group statements atomically

```go
tx, err := db.BeginTx(ctx, nil)
if err != nil { return err }
defer tx.Rollback() // no-op if Commit already succeeded

if _, err := tx.ExecContext(ctx, "UPDATE accounts SET balance = balance - ? WHERE id = ?", amount, from); err != nil {
    return err
}
if _, err := tx.ExecContext(ctx, "UPDATE accounts SET balance = balance + ? WHERE id = ?", amount, to); err != nil {
    return err
}
return tx.Commit()
```

The `defer tx.Rollback()` immediately after `BeginTx` is a standard, safe idiom: if `Commit()` already succeeded, the deferred `Rollback()` is a harmless no-op; if any statement failed and you returned early, it cleans up automatically.

### 4. Always use parameterized queries, never string concatenation

```go
// SAFE
db.QueryContext(ctx, "SELECT * FROM users WHERE email = $1", email)

// UNSAFE — SQL injection
db.QueryContext(ctx, "SELECT * FROM users WHERE email = '"+email+"'")
```

Parameterized queries (`$1`, `?`, or driver-specific placeholders) aren't just a best practice, they're a correctness and security requirement — string concatenation is a direct SQL injection vector.

### 5. Idempotency, first pass

```go
// Not idempotent: re-running doubles the balance
UPDATE accounts SET balance = balance + 100 WHERE id = 1;

// Idempotent (if request_id is unique + checked): safe to retry
INSERT INTO applied_credits (request_id, account_id, amount)
VALUES ($1, $2, $3) ON CONFLICT (request_id) DO NOTHING;
```

An operation is idempotent if running it twice (due to a retry, a duplicate message, a client double-click) produces the same result as running it once. This matters enormously once retries enter the picture — covered in depth at middle level.

---

## Code Examples

### Example 1 — Query, scan into a struct

```go
type User struct{ ID int; Name string }

func getUser(ctx context.Context, db *sql.DB, id int) (User, error) {
    var u User
    err := db.QueryRowContext(ctx, "SELECT id, name FROM users WHERE id = $1", id).
        Scan(&u.ID, &u.Name)
    if errors.Is(err, sql.ErrNoRows) {
        return User{}, ErrNotFound
    }
    return u, err
}
```

### Example 2 — A transactional transfer

```go
func transfer(ctx context.Context, db *sql.DB, from, to int, amount int) error {
    tx, err := db.BeginTx(ctx, nil)
    if err != nil { return err }
    defer tx.Rollback()

    if _, err := tx.ExecContext(ctx, "UPDATE accounts SET balance = balance - $1 WHERE id = $2", amount, from); err != nil {
        return err
    }
    if _, err := tx.ExecContext(ctx, "UPDATE accounts SET balance = balance + $1 WHERE id = $2", amount, to); err != nil {
        return err
    }
    return tx.Commit()
}
```

### Example 3 — Iterating rows and always closing

```go
rows, err := db.QueryContext(ctx, "SELECT id, name FROM users")
if err != nil { return err }
defer rows.Close()

for rows.Next() {
    var u User
    if err := rows.Scan(&u.ID, &u.Name); err != nil { return err }
    users = append(users, u)
}
return rows.Err() // always check after the loop — a mid-scan error doesn't panic, it just ends iteration
```

---

## Pros & Cons

| | Pros | Cons |
|---|---|---|
| **`database/sql` pooling** | Safe for concurrent use, no manual connection management | Requires understanding pool-size settings to tune for load |
| **Transactions** | Atomic multi-statement correctness | Holding one open too long blocks other operations on the same rows |
| **Parameterized queries** | Prevents SQL injection, lets the driver handle escaping | None — always use them |

---

## Use Cases

| Situation | Approach |
|---|---|
| Multiple related writes that must all succeed or none | Wrap in a transaction |
| A read that might legitimately return nothing | Check `errors.Is(err, sql.ErrNoRows)` |
| A write that might be retried by the caller | Design for idempotency (unique request ID, `ON CONFLICT DO NOTHING`) |

---

## Best Practices

1. Create one `*sql.DB` at startup; never per-request.
2. Always `defer rows.Close()` after `Query`, and check `rows.Err()` after the loop.
3. Always use parameterized queries.
4. Wrap related writes in a transaction with `defer tx.Rollback()` immediately after `BeginTx`.
5. Pass `context.Context` to every `...Context` method so queries respect cancellation/timeouts.

---

## Edge Cases & Pitfalls

- **Forgetting `rows.Close()`** leaks a connection from the pool, eventually starving it.
- **A long-running transaction holding row locks** blocks other queries/transactions touching the same rows — keep transactions short.
- **`sql.ErrNoRows` from `QueryRow` is expected, not exceptional** — always check for it explicitly rather than treating every query error the same way.

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| Opening a new `sql.DB` per request | Open once at startup, reuse the pool |
| String-concatenated SQL | Parameterized queries, always |
| Not checking `rows.Err()` after a scan loop | Always check it — a mid-loop error is silent otherwise |
| Assuming a write can't be retried/duplicated | Design idempotency in from the start for anything that might be retried |

---

## Cheat Sheet

```go
db.SetMaxOpenConns(25); db.SetConnMaxLifetime(5 * time.Minute)
tx, _ := db.BeginTx(ctx, nil); defer tx.Rollback()
tx.Commit()
rows, _ := db.QueryContext(ctx, q); defer rows.Close()
for rows.Next() { rows.Scan(&x) }
rows.Err() // check after loop
```

---

## Summary

- `sql.DB` is a connection pool, created once at startup and reused everywhere.
- Transactions group statements atomically; `defer tx.Rollback()` right after `BeginTx` is the safe standard idiom.
- Always use parameterized queries — never string concatenation.
- Always close `rows` and check `rows.Err()` after iterating.
- Idempotency — designing operations to be safe to retry — matters the moment retries or duplicate messages are possible.

---

## Further Reading

- Go Wiki — *database/sql Tutorial*: <https://go.dev/wiki/SQLInterface>
- `database/sql` package docs: <https://pkg.go.dev/database/sql>

---

## Related Topics

- [Error Handling](../04-error-handling/junior.md) — `sql.ErrNoRows` as a sentinel error.
- [HTTP and APIs](../05-http-and-apis/junior.md) — the layer that usually calls into this one.
