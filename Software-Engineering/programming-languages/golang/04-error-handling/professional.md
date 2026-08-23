# Error Handling — Professional Level

> **Topic:** [Error Handling](../README.md)
> **Focus:** Standardizing error taxonomies across an organization's services, error-handling conventions in code review, and postmortem practices for incidents rooted in poor error handling.

---

## Introduction

At professional level, error handling becomes an organizational convention, not just a per-service design. Dozens of services with inconsistent error kinds, inconsistent client/server fault classification, and inconsistent logging make cross-service incident response slower than it needs to be — the professional-level job is closing that gap.

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

## Pros & Cons

| Approach | Pros | Cons |
|---|---|---|
| Shared error-kind vocabulary | Faster cross-service incident response, less translation cost | Requires org-wide adoption and governance of the shared package |
| Lint-enforced error checking (`errcheck`, `wrapcheck`) | Prevents silent regressions | Initial rollout on an existing codebase can surface a large backlog of violations |
| Postmortems tracing to the error-handling root cause | Produces structural fixes, not just symptom patches | Requires discipline to look past the immediate symptom |

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

## Cheat Sheet

```
Org-wide error checklist:
  [ ] Shared error-kind vocabulary adopted
  [ ] errcheck / wrapcheck enforced in CI
  [ ] Code review checklist includes error classification + leak check
  [ ] Postmortems trace to the error-handling root cause, not just the symptom
```

---

## Summary

- A shared, org-wide error-kind vocabulary reduces cross-service incident-response friction.
- Enforce error-checking and wrapping discipline with linters in CI, not just code review vigilance.
- Postmortems for error-handling-rooted incidents should produce a structural fix, not a symptom patch.
- Error-handling inconsistency is technical debt that specifically taxes incident response — track and pay it down deliberately.

---

## Further Reading

- `errcheck`: <https://github.com/kisielk/errcheck>
- `golangci-lint` (bundles errcheck, staticcheck, and more): <https://golangci-lint.run/>

---

## Related Topics

- [Interfaces — Professional](../03-interfaces/professional.md) — the same shared-vocabulary principle applies to interface governance.
- [Production Debugging — Professional](../07-production-debugging/professional.md)
