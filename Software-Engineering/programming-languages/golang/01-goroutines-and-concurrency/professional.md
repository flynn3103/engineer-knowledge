# Goroutines and Concurrency — Professional Level

> **Topic:** [Goroutines and Concurrency](../README.md)
> **Focus:** Setting concurrency conventions across a team/org, reviewing concurrent code, incident response for concurrency bugs, and the organizational cost of "everyone invents their own pattern."

---

## Introduction

At this level, the challenge isn't writing correct concurrent code yourself — it's ensuring a team of engineers with varying experience levels writes concurrent code that's correct, consistent, and debuggable *without you reviewing every line*. That means conventions, shared libraries, review checklists, and a plan for the 2 a.m. page when a goroutine leak finally tips a service over.

---

## Core Concepts

### 1. Standardize the primitives, not just the style

A team where every engineer hand-rolls their own worker pool, their own cancellation wrapper, and their own retry-with-backoff will accumulate a dozen subtly different bugs. Publish and require use of a small internal package: one dispatcher, one `errgroup`-based helper, one context-aware retry function. Code review should treat a hand-rolled alternative as a red flag requiring justification, not a style preference.

### 2. Concurrency bugs are disproportionately expensive to review

A logic bug is usually visible in the diff. A concurrency bug (a missing lock, a channel that can leak, a context that isn't propagated) is often invisible in the diff and only manifests under load or a specific interleaving. Reviewers need a checklist, not just intuition: does every goroutine have a visible exit path? Is `context` threaded all the way through? Is there a test that would catch a regression here (ideally with `-race` and `goleak`)?

### 3. Incident response for concurrency issues has a specific shape

Symptoms are usually indirect: rising memory, rising goroutine count, increasing latency with no increase in traffic, or a hard deadlock that looks like the service "just stopped." The first diagnostic step is always the same regardless of symptom: pull a goroutine profile (`/debug/pprof/goroutine?debug=2`) and look for (a) an unusually large count of goroutines sharing one stack (a leak), or (b) goroutines blocked on each other in a cycle (a deadlock).

### 4. Postmortems should produce a shared primitive, not just a fix

When a concurrency incident is resolved, the fix for *that* call site is necessary but not sufficient. If the root cause was "no timeout on a network call," the postmortem action item should be a lint rule, a code-review checklist item, or a wrapper that makes the safe path the *only* path — not just a one-line patch to the affected function.

### 5. Teach the mental model, not just the API

Engineers who understand *why* a goroutine leak happens (no reachable exit path) debug novel leaks they've never seen before. Engineers who memorize "always call `wg.Done()`" only recognize the exact pattern they were taught. Invest in onboarding material that builds the mental model — CSP-style "goroutines communicate over channels, and every goroutine needs a plan to stop."

---

## Code Examples

### Example 1 — A minimal internal concurrency package (the kind worth standardizing on)

```go
// internal/conc/dispatch.go
package conc

type Dispatcher struct{ sem chan struct{} }

func NewDispatcher(n int) *Dispatcher { return &Dispatcher{sem: make(chan struct{}, n)} }

func (d *Dispatcher) Run(ctx context.Context, fn func(context.Context) error) error {
    select {
    case d.sem <- struct{}{}:
        defer func() { <-d.sem }()
        return fn(ctx)
    case <-ctx.Done():
        return ctx.Err()
    }
}
```

Every service imports this instead of writing its own semaphore. One place to fix bugs, one place to add metrics.

### Example 2 — A review checklist as a PR template snippet

```markdown
### Concurrency checklist (delete if not applicable)
- [ ] Every goroutine started here has a documented exit condition
- [ ] `context.Context` is threaded through, not created fresh mid-chain
- [ ] Shared state is protected by a mutex or owned by exactly one goroutine
- [ ] A test exercises this with `-race`
```

---

## Pros & Cons

| Approach | Pros | Cons |
|---|---|---|
| Mandating a shared internal concurrency package | Consistency, fewer novel bugs, centralized fixes | Requires buy-in and maintenance; can feel restrictive for genuinely novel cases |
| Checklist-driven review | Catches invisible-in-diff bugs | Only as good as the checklist; needs periodic revision as new bug classes appear |

---

## Best Practices

1. Maintain one internal package for bounded concurrency, retries, and cancellation — treat divergence as a review flag.
2. Require `-race` in CI for every service that uses goroutines beyond trivial fire-and-forget logging.
3. Make goroutine-count and key concurrency metrics part of every service's standard dashboard, not something added after an incident.
4. Turn every concurrency postmortem into a structural fix (lint rule, shared helper, checklist item), not just a patched call site.

---

## Postmortem Template (Concurrency Incident)

```
Symptom: (rising goroutine count / deadlock / latency spike)
First detected: (alert / user report / manual investigation)
Root cause: (missing timeout / missing lock / unbounded fan-out / ...)
Immediate fix: (patch applied)
Structural fix: (shared helper / lint rule / checklist update)
Owner + due date for structural fix:
```

---

## Edge Cases & Pitfalls

- **A shared internal concurrency package becomes a single point of failure** if it has its own bug — treat it with the same rigor (tests, `-race`, review) as any critical infrastructure.
- **Checklists rot** if not revisited after each new incident — schedule a periodic review.

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| Letting every team reinvent worker pools independently | Publish and mandate a shared internal package |
| Treating a concurrency incident's fix as "done" once the patch ships | Require a structural action item before closing the postmortem |
| Reviewing concurrent PRs the same way as sequential logic PRs | Use a concurrency-specific checklist |

---

## Cheat Sheet

```
Incident response for "goroutines/memory climbing":
  1. Pull goroutine profile: /debug/pprof/goroutine?debug=2
  2. Group by stack trace — find the dominant leaking stack
  3. Identify missing exit condition (timeout / closed channel / canceled ctx)
  4. Patch + add goleak-covered regression test
  5. File structural follow-up (shared helper / lint rule)
```

---

## Summary

- The professional-level job is making correct concurrency the *default*, not the exception, across a team.
- Standardize on a small set of shared, well-tested concurrency primitives instead of letting every engineer reinvent them.
- Concurrency bugs need their own review checklist because they're invisible in a plain diff read.
- Every concurrency postmortem should produce a structural fix — a shared helper, lint rule, or checklist update — not just a patched call site.

---

## Further Reading

- *The Go Memory Model*: <https://go.dev/ref/mem>
- Google SRE Book — *Managing Incidents*: <https://sre.google/sre-book/managing-incidents/>

---

## Related Topics

- [Production Debugging — Professional](../07-production-debugging/professional.md) — organizational incident response for live services.
