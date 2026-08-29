# Go Runtime — Middle

> **Topic:** [Go Runtime](../README.md)
> **Focus:** The GMP scheduler in more depth, work-stealing, cooperative and async preemption, the tri-color mark-and-sweep GC cycle, and reading `GODEBUG=gctrace=1` output.

---

## Introduction

At junior level you learned the runtime schedules goroutines and collects garbage. Now the question is *how* — specifically, how the scheduler decides who runs where, what "preemption" means for a language without OS-level thread interruption by default, and how the GC's tri-color algorithm lets it run concurrently with your program without corrupting memory.

---

## Prerequisites

- Comfortable with `GOMAXPROCS`, escape analysis, and basic GC concepts (junior level).

---

## Core Concepts

### 1. GMP: Goroutines, Machines, Processors

- **G (Goroutine)** — a unit of work: stack, program counter, state.
- **M (Machine)** — an OS thread.
- **P (Processor)** — a scheduling context; there are `GOMAXPROCS` of them. A P must be held by an M for that M to run Go code. Each P has a local run queue of Gs.

An M without a P can't execute Go code (it might be blocked in a syscall). This separation is what lets Go scale to many more Ms than `GOMAXPROCS` when goroutines block on syscalls, while still capping actual parallel Go execution at `GOMAXPROCS`.

### 2. Work-stealing keeps Ps busy

When a P's local run queue is empty, it steals goroutines from another P's queue (half of it, at a time) rather than sitting idle. This keeps CPU utilization high without a global lock on every scheduling decision — only stealing needs cross-P coordination.

### 3. Preemption: cooperative, then asynchronous

Historically, a goroutine only yielded at specific points (function calls). A goroutine stuck in a tight loop with no function calls could starve others on the same P. Since Go 1.14, the runtime does **asynchronous preemption**: it can interrupt a running goroutine via a signal even mid-loop, based on a background monitor thread (`sysmon`) noticing a goroutine has run too long. This closed a longstanding class of "why is my whole program frozen" bugs.

### 4. The GC is tri-color mark-and-sweep, running concurrently

Conceptually, every object starts **white** (unvisited). The GC marks reachable objects **grey** (queued to scan) then **black** (scanned, definitely reachable). When no grey objects remain, everything still white is garbage. Because your program (the "mutator") keeps running and can create new pointers *while* this is happening, Go uses a **write barrier** — extra bookkeeping code inserted around pointer writes during the mark phase — to ensure the invariant "no black object points to a white object" holds, which is what makes concurrent marking safe.

### 5. Reading `GODEBUG=gctrace=1`

```bash
GODEBUG=gctrace=1 ./myservice
gc 12 @3.512s 2%: 0.02+1.2+0.01 ms clock, 0.2+0.5/1.1/0+0.1 ms cpu, 8->10->4 MB, 9 MB goal, 8 P
```

Key fields: the `2%` is the fraction of total CPU time spent in this GC cycle; `8->10->4 MB` is heap size before the cycle, at the mark-termination point, and after sweeping (live heap); `9 MB goal` is the trigger for the *next* cycle. A rising "live heap" over many cycles despite steady-state traffic is a strong memory-leak signal.

### 6. Stack growth is a copy, not an extension

When a goroutine's stack fills, the runtime allocates a new, larger stack segment (typically double), copies the old stack's contents over, and **rewrites every pointer that pointed into the old stack** to point into the new one. This is why Go stacks must be *movable* — and why you can't take the address of a stack variable and expect it to be stable across an arbitrary amount of further execution in a way that outlives potential stack growth (the compiler handles this correctly for you, but it's why "just cast the pointer" tricks that work in C don't translate).

---

## Code Examples

### Example 1 — Observing work-stealing indirectly via `GOMAXPROCS`

```go
runtime.GOMAXPROCS(1)
// spawn many CPU-bound goroutines; they now time-slice on a single P
// via async preemption instead of running in parallel
```

### Example 2 — Forcing and timing a GC cycle

```go
start := time.Now()
runtime.GC()
fmt.Println("GC took", time.Since(start))
```

`runtime.GC()` forces a full, blocking (from the caller's perspective) garbage collection — useful in benchmarks and diagnostics, never in a hot path.

### Example 3 — `GODEBUG` for scheduler tracing

```bash
GODEBUG=schedtrace=1000 ./myservice
SCHED 1000ms: gomaxprocs=8 idleprocs=3 threads=12 spinningthreads=1 idlethreads=4 runqueue=2 [3 1 0 5 2 0 1 4]
```

`runqueue` per-P shows load imbalance; a consistently empty run queue on some Ps while others stay full over time suggests work isn't distributing the way you'd expect (though the scheduler will steal to rebalance).

---

## Pros & Cons

| | Pros | Cons |
|---|---|---|
| Work-stealing scheduler | High CPU utilization without a global lock | Scheduling decisions are largely opaque; hard to force specific placement |
| Async preemption (1.14+) | Tight CPU-bound loops no longer starve the runtime | Adds signal-handling complexity under the hood (mostly invisible to you) |
| Concurrent tri-color GC | Sub-millisecond STW pauses even on large heaps | Write barriers add a small constant overhead to every pointer write during marking |

---

## Use Cases

| Situation | Tool |
|---|---|
| Diagnosing scheduler load imbalance | `GODEBUG=schedtrace=1000` |
| Diagnosing GC frequency/pause impact | `GODEBUG=gctrace=1` |
| Confirming a heap leak vs. steady-state churn | Watch the "live heap after sweep" number across many `gctrace` lines |

---

## Best Practices

1. Use `gctrace=1` in a staging environment under load before concluding GC is or isn't a bottleneck.
2. Don't call `runtime.GC()` in production hot paths — it's for diagnostics and benchmarks.
3. Trust the scheduler's work-stealing; don't try to manually pin goroutines to Ps as a first resort.
4. Treat a steadily rising "live heap after sweep" as a leak signal worth a `pprof` heap profile.

---

## Edge Cases & Pitfalls

- **`GOMAXPROCS(1)` does not disable preemption** — goroutines still time-slice, just without true parallelism.
- **Write barriers mean GC has a real (small) cost even outside STW pauses** — "concurrent" doesn't mean "free."
- **A very large single allocation** can trigger GC on its own regardless of `GOGC`, since the pacer accounts for it immediately.

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| Assuming `GOMAXPROCS(1)` means single-threaded, sequential execution | Goroutines still interleave via preemption — races are still possible |
| Reading one `gctrace` line and concluding "GC is fine/bad" | Look at the trend across many cycles, especially the live-heap number |
| Manually trying to control scheduling via `runtime.Gosched()` | Rarely needed since 1.14's async preemption; usually a sign of a different design problem |

---

## Tricky Points

- A goroutine can migrate between Ms across its lifetime — there's no thread affinity by default.
- `sysmon` (the system monitor) runs independently of any P and is what detects long-running goroutines for async preemption and drives GC pacing decisions.
- The write barrier is active only during the concurrent mark phase, not the entire GC cycle.

---

## Cheat Sheet

```
GODEBUG=gctrace=1        — per-cycle GC stats
GODEBUG=schedtrace=1000  — per-P run queue + thread stats every 1000ms
runtime.GC()             — force a blocking GC (diagnostics/benchmarks only)
GMP: Goroutine → Processor (GOMAXPROCS of them) → Machine (OS thread)
```

---

## Summary

- GMP: goroutines are scheduled onto Ps (bounded by `GOMAXPROCS`), which are held by Ms (OS threads); idle Ps steal work from busy ones.
- Since Go 1.14, preemption is asynchronous — tight loops no longer starve the scheduler.
- The GC is concurrent tri-color mark-and-sweep, safe alongside your running program via write barriers, with very short stop-the-world pauses.
- `GODEBUG=gctrace=1` and `schedtrace=...` are the primary windows into what the runtime is actually doing.

---

## Further Reading

- *Analysis of the Go runtime scheduler* — <https://www.cs.columbia.edu/~aho/cs6998/reports/12-12-11_DeshpandeSponslerDeshpande_GO.pdf>
- The Go Blog — *Go GC: Prioritizing low latency and simplicity*: <https://go.dev/blog/go15gc>

---

## Related Topics

- [Goroutines and Concurrency — Middle](../01-goroutines-and-concurrency/middle.md)
- [Production Debugging](../07-production-debugging/middle.md) — turning `gctrace`/`schedtrace` output into action.

---

## Check your understanding

1. Explain Go Runtime — Middle Level in your own words and name the problem it solves.
2. How would you apply the ideas around Introduction, Prerequisites, Core Concepts in a realistic engineering change?
3. What failure mode or misuse should you look for, and what evidence would reveal it?
4. Which local design trade-off would make you choose or reject Go Runtime — Middle Level in an existing codebase?
5. What observable result would convince you that the approach improved the system?
