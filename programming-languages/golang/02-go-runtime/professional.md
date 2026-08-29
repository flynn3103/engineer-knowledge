# Go Runtime — Professional

<!-- level-focus -->
At professional level, focus on this question:

> How should teams adopt and operate **Go Runtime** with measurable outcomes and limited coordination?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Fleet-wide runtime defaults belong in shared infrastructure, not per-service tribal knowledge

Every service should inherit sane defaults — `automaxprocs` for CPU-aware `GOMAXPROCS`, a `GOMEMLIMIT` derived automatically from the container's memory request/limit — from a shared base image or bootstrap library, rather than each team rediscovering these settings after their own incident.

### 2. Capacity planning must account for GC CPU overhead explicitly

When sizing a service's CPU request, GC overhead (commonly 5–25% of CPU time depending on allocation rate) needs to be part of the budget, not a surprise discovered under load. Load-testing with `gctrace=1` enabled and recording the GC CPU percentage as a first-class metric during capacity reviews prevents under-provisioning.

### 3. Distinguish a runtime problem from an architecture problem

A team reporting "GC is killing our latency" sometimes has a genuine allocation-rate problem fixable with pooling — and sometimes has an architecture doing far more allocation than the workload requires (e.g., deserializing a full object graph to read one field, or building a new large struct per item in a loop that could be an index lookup). The professional-level skill is recognizing which one you're looking at: if allocation reduction only buys 10–20%, the deeper issue is usually the algorithm or data flow, not the runtime.

### 4. Standardize the diagnostic playbook, not just the fix

Every service should have a documented, consistent way to answer "is this a GC problem?": pull `gctrace`, pull a heap profile, compare `allocs/op` on the relevant hot path against its historical baseline. Without a shared playbook, each team reinvents (or skips) this diagnosis under incident pressure.

### 5. Runtime version upgrades are a fleet-wide lever

Go release notes regularly include scheduler and GC improvements (async preemption in 1.14, the pacer redesign around `GOMEMLIMIT` in 1.19, PGO in 1.21+) that measurably improve latency and throughput for free. Treating Go version upgrades as routine, tested, fleet-wide rollouts — rather than an afterthought — captures real performance wins with no code change.

---

## Code Examples

### Example 1 — Shared bootstrap defaults

```go
// internal/bootstrap/runtime.go
package bootstrap

import _ "go.uber.org/automaxprocs"

func init() {
    if limit, ok := os.LookupEnv("MEM_LIMIT_BYTES"); ok {
        // derive GOMEMLIMIT as ~90% of the container's memory limit
        setMemLimit(limit)
    }
}
```

Every service imports `internal/bootstrap` once, and gets consistent, container-aware runtime defaults without each team hand-deriving them.

---

## Best Practices

1. Bake `automaxprocs` and a `GOMEMLIMIT` derivation into a shared bootstrap library used by every service.
2. Include GC CPU percentage in load-test reports used for capacity planning.
3. Maintain a documented diagnostic playbook: `gctrace` → heap profile → `allocs/op` baseline comparison.
4. Treat Go version bumps as a routine, low-risk win to schedule periodically, not a project to defer indefinitely.
5. When a team reports a GC problem, ask "how much does reducing allocation actually buy?" before accepting GC tuning as the fix — a small win points at a deeper architectural issue.

---

## Edge Cases & Pitfalls

- **A shared runtime bootstrap library with a bug affects every service simultaneously** — test it with the same rigor as any critical shared dependency.
- **Go version upgrades occasionally change GC pacing behavior** enough to shift memory/CPU trade-offs — canary the upgrade under real load before a fleet-wide rollout.

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| Every team hand-tuning `GOMAXPROCS`/`GOMEMLIMIT` independently | Centralize in a shared bootstrap library |
| Sizing CPU requests without accounting for GC overhead | Include GC CPU % in load-test-driven capacity planning |
| Treating every "GC is slow" report as a tuning problem | Check whether allocation reduction actually moves the needle; if not, look at the architecture |

---

## Apply it

1. Define the user or business outcome that **Go Runtime** should improve.
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

- Which measurable outcome justifies investing in Go Runtime?
- Which team owns the full lifecycle and incident response?
- What reversible increment produces the earliest useful evidence?
- Which exit condition proves that migration or adoption is complete?
