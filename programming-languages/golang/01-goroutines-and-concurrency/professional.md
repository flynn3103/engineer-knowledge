# Goroutines and Concurrency — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Goroutines and Concurrency** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
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

## Apply it

1. Define the user or business outcome that **Goroutines and Concurrency** should improve.
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

- Which measurable outcome justifies investing in Goroutines and Concurrency?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
