# Error Handling — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Error Handling** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. A shared error-kind vocabulary across services

If every service invents its own `Kind` enum with different names for the same underlying concepts (`NotFound` vs `Missing` vs `404Error`), engineers debugging a multi-service incident pay a real cognitive tax translating between them. A shared internal library defining a small, common set of error kinds — adopted org-wide — removes that translation cost.

### 2. Code review conventions for error handling

A lightweight, written checklist reviewers apply consistently:

- Is every error checked, not discarded?
- Is wrapping done with `%w`, preserving inspectability?
- Is the error classified (client vs. server fault) correctly?
- Does a client-facing error leak internal detail?
- Is a request/trace ID attached before logging?

Without an explicit checklist, error-handling quality varies by reviewer attention and mood — codifying it produces consistent outcomes.

### 3. Postmortems should trace back to the error-handling decision, not just the symptom

"The database connection pool exhausted" is a symptom. The professional-level postmortem asks: was there a retry loop that didn't back off? Was a transient error incorrectly classified as fatal (or vice versa)? Was a `context` deadline missing, letting a slow query hold a connection indefinitely? The structural fix usually lives in the error-handling/retry logic, not just in scaling the pool.

### 4. Error-handling debt accumulates like any other technical debt

A codebase where errors are inconsistently wrapped, sometimes discarded, sometimes logged three times as they propagate, is a form of technical debt that specifically taxes incident response speed — the worst possible time for that tax to be due. Treating error-handling consistency as a tracked quality metric (e.g., via a linter checking for discarded errors, or an `errcheck`/`staticcheck` gate in CI) keeps the debt from silently accumulating.

### 5. Teaching the client/server fault distinction early

Engineers new to distributed systems often don't intuitively separate "the caller did something wrong" from "we failed to serve a valid request" — both feel like "an error happened." Making this distinction explicit and central in onboarding material, and enforcing it via the shared error-kind vocabulary (concept 1), pays off in every alerting decision made afterward.

---

## Code Examples

### Example 1 — Enforcing error checking in CI

```bash
errcheck ./...
# handler.go:42:2: f.Close()  # unchecked error return
```

```yaml
# .golangci.yml (excerpt)
linters:
  enable:
    - errcheck
    - wrapcheck  # flags errors returned without wrapping
```

### Example 2 — A shared error-kind package used org-wide

```go
// company.com/pkg/apperr
type Kind int
const (
    KindNotFound Kind = iota
    KindInvalidInput
    KindUnauthorized
    KindUnavailable
    KindInternal
)
```

Every service imports this instead of defining its own enum — a small, deliberate act of standardization with outsized payoff during cross-service incidents.

---

## Best Practices

1. Publish and mandate a shared error-kind vocabulary across services, rather than letting each team invent its own.
2. Enforce error-checking and wrapping conventions with linters (`errcheck`, `wrapcheck`, `staticcheck`) in CI.
3. Include an error-handling checklist in code review guidelines, applied consistently.
4. Require postmortems for error-handling-rooted incidents to identify the structural fix, not just patch the symptom.

---

## Edge Cases & Pitfalls

- **Rolling out `errcheck` on a large existing codebase** can surface hundreds of pre-existing violations — plan a staged rollout (new code only, then a scheduled cleanup) rather than blocking all work at once.
- **A shared error-kind package that's too coarse** (only 3 kinds for a genuinely diverse set of failure modes) forces awkward overloading of a single kind for unrelated failures — review and evolve it as real usage reveals gaps.

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| Every team maintaining its own error-kind enum | Adopt a shared, org-wide vocabulary |
| No linter enforcement for discarded/unwrapped errors | Add `errcheck`/`wrapcheck` to CI, staged if the codebase is large |
| Postmortems that stop at "we scaled the connection pool" | Trace back to the error-handling/retry decision that caused exhaustion |

---

## Apply it

1. Define the user or business outcome that **Error Handling** should improve.
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

- Which measurable outcome justifies investing in Error Handling?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
