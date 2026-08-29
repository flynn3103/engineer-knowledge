# Go Runtime — Professional

> **Topic:** [Go Runtime](../README.md)
> **Focus:** Setting runtime-tuning conventions across services, capacity planning around GC behavior, and knowing when a "runtime problem" is actually an architecture problem.

---

## Introduction

At the professional level, runtime tuning stops being a per-service tweak and becomes an organizational concern: what are the default `GOMAXPROCS`/`GOMEMLIMIT` settings for every service in the fleet, how do you catch allocation regressions before they reach production, and how do you tell engineers "this isn't a GC problem, your architecture is doing 100x more work than it needs to"?

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

## Pros & Cons

| Approach | Pros | Cons |
|---|---|---|
| Fleet-wide runtime defaults library | Consistency, fewer "we forgot to set GOMAXPROCS" incidents | Requires adoption discipline; a bug in the shared library affects everything |
| GC CPU as a capacity-planning input | Prevents under-provisioning surprises | Requires load-testing with realistic allocation patterns, not synthetic no-op load |
| Treating Go upgrades as routine | Captures free scheduler/GC improvements | Requires a tested upgrade pipeline; some upgrades do carry behavior changes worth reviewing |

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

## Cheat Sheet

```
Fleet checklist:
  [ ] automaxprocs (or equivalent) in every service's bootstrap
  [ ] GOMEMLIMIT derived from container memory limit
  [ ] GC CPU % tracked in load-test/capacity reports
  [ ] Documented diagnostic playbook: gctrace -> heap profile -> allocs/op baseline
  [ ] Go version upgrades scheduled routinely, not deferred indefinitely
```

---

## Summary

- Runtime tuning at scale is an organizational default, not a per-service afterthought — centralize `GOMAXPROCS`/`GOMEMLIMIT` derivation.
- GC CPU overhead is a real capacity-planning input; measure it under realistic load, not synthetic no-op traffic.
- Learn to distinguish a genuine allocation problem from an architecture doing unnecessary work — small wins from pooling point at the latter.
- Go version upgrades are a recurring, low-effort source of real scheduler/GC improvements — treat them as routine.

---

## Further Reading

- Go release notes (scan for "runtime" and "GC" sections each release): <https://go.dev/doc/devel/release>

---

## Related Topics

- [Production Debugging — Professional](../07-production-debugging/professional.md)

---

## Check your understanding

1. Explain Go Runtime — Professional Level in your own words and name the problem it solves.
2. How would you apply the ideas around Introduction, Core Concepts, Code Examples in a realistic engineering change?
3. What failure mode or misuse should you look for, and what evidence would reveal it?
4. How would you introduce and govern Go Runtime — Professional Level across teams through reversible, measurable increments?
5. What observable result would convince you that the approach improved the system?
