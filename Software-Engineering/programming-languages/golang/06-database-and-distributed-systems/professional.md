# Database and Distributed Systems — Professional Level

> **Topic:** [Database and Distributed Systems](../README.md)
> **Focus:** Data-consistency standards across an organization, capacity planning for shared databases, leading a data-loss or data-corruption incident, and governance for idempotency/locking conventions fleet-wide.

---

## Introduction

At professional level, data-correctness decisions ripple across every team sharing infrastructure. An under-provisioned connection pool policy, an inconsistent idempotency convention, or a poorly reviewed distributed lock affects everyone using the same database or coordination service — this level is about the governance that keeps those shared foundations reliable.

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

## Pros & Cons

| Approach | Pros | Cons |
|---|---|---|
| Shared idempotency-key standard/library | Prevents cross-team boundary bugs | Requires org-wide adoption and a migration for existing endpoints |
| Documented per-service connection budgets | Prevents self-inflicted pool exhaustion at scale | Requires an ongoing review process as services scale |
| Stop-assess-remediate-then-root-cause incident order | Minimizes blast radius during active data incidents | Requires training; instinct under pressure often skips to root-cause first |

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

## Cheat Sheet

```
Org-wide data-correctness checklist:
  [ ] Standardized idempotency-key format/library, adopted across write endpoints
  [ ] Documented, reviewed connection budgets per service on shared databases
  [ ] Data-incident response order: stop -> assess blast radius -> remediate -> root-cause
  [ ] Postmortems audit idempotency/locking coverage explicitly
  [ ] Migrations: backward-compatible only, tested at production-like data volume
```

---

## Summary

- Idempotency-key conventions need to be standardized org-wide, not left to per-team invention, since they often cross service boundaries.
- Shared databases need documented, enforced per-service connection budgets, reviewed at every scale-up.
- Data-correctness incidents have a distinct response order: stop the write path, assess blast radius, remediate, then root-cause — not the reverse.
- Postmortems for data incidents should explicitly audit idempotency and locking coverage fleet-wide, not just fix the one affected path.
- Migration governance (backward-compatible only, production-volume tested) prevents an entire class of self-inflicted incidents.

---

## Further Reading

- Google SRE Book — *Data Integrity: What You Read Is What You Wrote*: <https://sre.google/sre-book/data-integrity/>

---

## Related Topics

- [HTTP and APIs — Professional](../05-http-and-apis/professional.md)
- [Production Debugging — Professional](../07-production-debugging/professional.md)
