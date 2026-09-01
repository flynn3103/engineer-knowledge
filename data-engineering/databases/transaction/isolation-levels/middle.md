# Isolation Levels — Middle

<!-- level-focus -->
At middle level, focus on this question:

> What exactly does each of the four standard isolation levels prevent and
> allow?

Prerequisite: [`junior.md`](junior.md).

---

## The standard ladder

```mermaid
flowchart LR
    RU["Read Uncommitted\n(rarely used in practice)"] --> RC["Read Committed\n(Postgres/Oracle default)"]
    RC --> RR["Repeatable Read\n(MySQL InnoDB default)"]
    RR --> SER["Serializable\n(strongest, most expensive)"]
```

| Level | Dirty read | Non-repeatable read | Phantom read | Notes |
|---|---|---|---|---|
| **Read Uncommitted** | ✅ Possible | ✅ Possible | ✅ Possible | Rarely implemented as truly distinct today; most engines treat it the same as Read Committed. |
| **Read Committed** | ❌ Prevented | ✅ Possible | ✅ Possible | You only ever see committed data, but a re-read within your own transaction can see newer commits. |
| **Repeatable Read** | ❌ Prevented | ❌ Prevented | ✅ Possible (varies by engine) | Re-reading the same row always gives the same value for the rest of your transaction. Postgres's implementation (snapshot-based) actually also prevents phantoms; the SQL standard doesn't require it. |
| **Serializable** | ❌ Prevented | ❌ Prevented | ❌ Prevented | Transactions behave *as if* run one at a time, in some order — the strongest guarantee, at the highest coordination cost. |

## Setting it explicitly

```sql
BEGIN;
SET TRANSACTION ISOLATION LEVEL REPEATABLE READ;
SELECT balance FROM accounts WHERE id = 'A';
-- ... more work in this same transaction, same snapshot the whole time ...
COMMIT;
```

Most application code never sets this explicitly and silently runs at
whatever the database's **default** is — which is a decision worth knowing
per database:

| Database | Default isolation level |
|---|---|
| PostgreSQL | Read Committed |
| Oracle | Read Committed |
| MySQL (InnoDB) | Repeatable Read |
| SQL Server | Read Committed |

## Why not just always use Serializable?

Serializable is implemented either with heavy locking (blocking concurrent
transactions that would conflict) or with conflict detection that **aborts
and retries** transactions that would have violated serializability. Both
cost throughput: more blocking, or more wasted work on aborted retries, under
contention. Most application workloads accept Read Committed or Repeatable
Read and handle the residual anomalies explicitly (row locking with
`SELECT ... FOR UPDATE`, application-level checks) rather than pay
Serializable's cost everywhere.

## Test yourself

1. Under Read Committed, can two sequential `SELECT`s in the same transaction
   return different values for the same row? Under Repeatable Read?
2. Why might a database vendor implement "Repeatable Read" using a mechanism
   that also happens to prevent phantom reads, even though the standard
   doesn't require it (this is exactly what Postgres does — see `senior.md`)?
3. If your ORM/driver never calls `SET TRANSACTION ISOLATION LEVEL`, what
   level is your application actually running at, for your specific database?

Continue to [`senior.md`](senior.md) for the anomaly Repeatable Read still
misses: write skew.
