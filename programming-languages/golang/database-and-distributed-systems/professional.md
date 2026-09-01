# Database and Distributed Systems — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Database and Distributed Systems** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Idempotency and retry conventions belong in a shared standard

If Team A's idempotency-key format and Team B's differ, and a request flows through both, the guarantee can silently break at the boundary. An org-wide standard (e.g., a required `Idempotency-Key` header format, a shared library that enforces the unique-constraint pattern) removes this class of cross-team bug.

### 2. Shared databases need explicit connection-budget governance

When multiple services share a database cluster, each team's `MaxOpenConns` choice affects every other tenant's available headroom. A professional-level practice is a documented, enforced connection budget per service (reviewed at onboarding and at every significant scale-up), rather than each team independently maximizing their own pool size.

### 3. Leading a data-loss or data-corruption incident has a specific shape

Unlike an availability incident, a data-correctness incident (duplicate charges, lost writes, corrupted state) usually requires: **stop the bleeding** (pause the offending write path), **assess blast radius** (which records, how many, since when — usually via a query against audit logs or a data warehouse), **decide on remediation** (reprocess, manually correct, or accept and communicate), and **only then** root-cause. Reversing this order — trying to fully understand root cause before stopping the ongoing damage — extends the blast radius unnecessarily.

### 4. Postmortems for data incidents should audit idempotency/locking coverage specifically

Beyond the immediate fix, the postmortem should ask: was this write path missing an idempotency key? Was a lock naive where it needed to be robust? Was a saga's compensating action not actually idempotent? These become concrete, fleet-wide action items (often "audit all write paths lacking idempotency keys," not just a fix to the one path involved).

### 5. Schema and migration governance prevents a whole class of incidents

A shared convention — backward-compatible migrations only (additive columns, no destructive renames without a multi-step deprecation), migrations reviewed and tested against production-like data volume before rollout — prevents an entire category of incident where a migration locks a large table for an unacceptable duration or breaks a still-deploying older service version reading the old schema.

---

## Code Examples

### Example 1 — A required idempotency-key convention, enforced by a shared library

```go
// company.com/pkg/idempotency
func RequireKey(r *http.Request) (string, error) {
    key := r.Header.Get("Idempotency-Key")
    if !isValidUUID(key) {
        return "", ErrMissingOrInvalidIdempotencyKey
    }
    return key, nil
}
```

Every write endpoint across the org calls this instead of inventing its own header name/validation.

### Example 2 — A connection-budget policy as a reviewable artifact

```yaml
# service.yaml (excerpt reviewed at scale-up time)
database:
  cluster: shared-primary
  max_open_conns_per_instance: 10
  expected_max_instances: 20   # => 200 of the cluster's budgeted 1000 connections
```

---

## Best Practices

1. Standardize idempotency-key format and enforcement via a shared library, not per-team convention.
2. Maintain and review documented connection budgets for every service sharing a database cluster.
3. Train and drill the stop-assess-remediate-then-root-cause order for data-correctness incidents specifically.
4. Make idempotency/locking coverage an explicit, standing postmortem audit question for data incidents.
5. Enforce backward-compatible-only migrations with production-data-volume testing before rollout.

---

## Edge Cases & Pitfalls

- **A connection-budget policy that's documented but never enforced** (no automated check against it) degrades into decoration — tie it to a CI check or a review gate at deploy/scale-up time.
- **A migration governance policy without production-data-volume testing** can still let a technically "backward compatible" migration lock a table long enough to cause a real incident on a much larger production table than staging ever exercised.

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| Each team inventing its own idempotency-key convention | Standardize via a shared library/header contract |
| No enforced connection-budget review at scale-up | Require it as part of the scaling change process |
| Root-causing a data-correctness incident before stopping the write path causing it | Train the stop-assess-remediate-then-root-cause order |

---

## Apply it

1. Define the user or business outcome that **Database and Distributed Systems** should improve.
2. Assign one owner for code, contracts, operations, and incidents.
3. Split delivery into reversible increments that produce evidence early.
4. Publish responsibilities, escalation paths, and compatibility windows.
5. Stop or expand only when the agreed measures support that decision.

## Verify your work

- Each increment has an owner, rollback path, and observable exit condition.
- Adoption, reliability, delivery time, and coordination cost are measured.
- Incident and migration exercises prove that responsibility is executable.
- The old path is removed only after telemetry proves it is unused.

## Review questions

- Which measurable outcome justifies investing in Database and Distributed Systems?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
