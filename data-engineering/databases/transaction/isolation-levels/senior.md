# Isolation Levels — Senior

<!-- level-focus -->
At senior level, focus on this question:

> What is write skew, and why does even "no visible anomaly" isolation
> (snapshot isolation) fail to prevent it?

Prerequisite: [`middle.md`](middle.md).

---

## Snapshot isolation vs. true serializability

Postgres's "Repeatable Read" and most engines' "Snapshot Isolation" give each
transaction a consistent snapshot of the database as of when it began — no
dirty reads, no non-repeatable reads, no phantoms *within that snapshot*.
This feels like Serializable. It is not.

## Write skew: the anomaly snapshot isolation misses

Two doctors, Alice and Bob, are both on call. Hospital rule: **at least one
doctor must be on call at all times.**

```mermaid
sequenceDiagram
    participant TxA as Txn A (Alice signs off)
    participant TxB as Txn B (Bob signs off)
    Note over TxA,TxB: Both start with snapshot:\nAlice on-call=true, Bob on-call=true
    TxA->>TxA: SELECT count(*) WHERE on_call -> 2, so it's safe to sign off
    TxB->>TxB: SELECT count(*) WHERE on_call -> 2, so it's safe to sign off
    TxA->>TxA: UPDATE alice SET on_call=false; COMMIT
    TxB->>TxB: UPDATE bob SET on_call=false; COMMIT
    Note over TxA,TxB: Both committed. Zero doctors\non call. Rule violated.
```

Each transaction only wrote to its **own** row — no dirty read, no
non-repeatable read, no phantom, nothing that Read Committed or Repeatable
Read even claims to catch, because neither transaction re-read a row the
other one wrote. Each read a **consistent but stale** snapshot, made a
decision based on it, and the two decisions combined into an invalid state.

This is **write skew**: two transactions read overlapping data, make disjoint
writes based on what they read, and the combination violates an invariant
that neither transaction individually violated.

## Only true Serializable (or explicit locking) prevents this

```sql
-- Option 1: force a real conflict with SELECT ... FOR UPDATE
BEGIN;
SELECT * FROM doctors WHERE on_call = true FOR UPDATE;  -- locks the rows
UPDATE doctors SET on_call = false WHERE name = 'Alice';
COMMIT;

-- Option 2: use SERIALIZABLE and let the database detect the conflict
BEGIN ISOLATION LEVEL SERIALIZABLE;
SELECT count(*) FROM doctors WHERE on_call = true;
UPDATE doctors SET on_call = false WHERE name = 'Alice';
COMMIT;  -- one of the two transactions will be forced to ABORT and retry
```

Under true Serializable, the database detects that both transactions' reads
and writes couldn't have been produced by *any* serial (one-at-a-time)
ordering, and forces one to abort. Your application must be prepared to
**retry aborted transactions** — Serializable isolation trades "silently
wrong" for "occasionally forced to retry," which is a trade worth taking for
invariants that actually matter.

> 🎯 **Senior takeaway:** "my transaction only reads what it needs and writes
> only its own row" is not sufficient reasoning for correctness under
> concurrency. If a business invariant spans multiple rows read by more than
> one concurrent transaction, only Serializable isolation (or explicit
> locking that manufactures a real conflict) protects it.

## Test yourself

1. Why does `SELECT ... FOR UPDATE` on the on-call rows fix the write-skew
   example, when neither transaction technically needed to *write* to the
   other doctor's row?
2. Construct your own write-skew example from an inventory system: two
   transactions each check "is there at least 1 unit left" before decrementing
   different SKUs that share a combined limit.
3. Why must application code be ready to retry a transaction under
   Serializable isolation, when it never needed to under Read Committed?

Continue to [`professional.md`](professional.md) to choose isolation levels
for real pipeline and replica workloads.
