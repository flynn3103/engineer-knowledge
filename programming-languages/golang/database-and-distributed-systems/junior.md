# Database and Distributed Systems — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Database and Distributed Systems** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
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

## Apply it

1. Choose one small, known input for **Database and Distributed Systems**.
2. Predict the output or observable behavior.
3. Run the smallest example or probe that exercises the concept.
4. Change one input to trigger a failure or boundary case.
5. Explain the evidence using the guide's vocabulary.

## Verify your work

- Record the exact input, command or code path, and output.
- Repeat the probe and confirm the result is consistent.
- Show one expected success and one expected failure.
- Resolve any difference between the prediction and the evidence.

## Review questions

- What problem does Database and Distributed Systems solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
