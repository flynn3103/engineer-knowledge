# Go Runtime — Interview Prep

> **Topic:** [Go Runtime](../README.md)

---

## Conceptual / Foundational

**Q: What is the GMP model?**
A: Goroutine (unit of work), Machine (OS thread), Processor (scheduling context, `GOMAXPROCS` of them). A P must be held by an M to run Go code; idle Ps steal work from busy ones.

**Q: Does Go have stop-the-world GC pauses?**
A: Yes, but very short (sub-millisecond) ones used for coordination — most of the mark phase runs concurrently with your program via a tri-color algorithm and write barriers.

**Q: What is escape analysis?**
A: A compile-time decision about whether a value's lifetime can be proven to stay within a function's stack frame (stack-allocated) or must be heap-allocated because a reference to it escapes the function.

**Q: What does `GOGC=100` mean?**
A: The GC targets running again once the heap has grown 100% (doubled) since the last cycle's live-heap size. Lower values trigger GC more often (less memory, more CPU); higher values less often.

## Tricky / Trap Questions

**Q: If I set `GOMAXPROCS(1)`, does my program become single-threaded and safe from races?**
A: No. Goroutines still interleave via preemption on that single P; races are still possible. `GOMAXPROCS(1)` limits parallelism, not concurrency.

**Q: A function returns a pointer to a local variable. Is that a dangling pointer bug, like in C?**
A: No — Go's escape analysis detects the value must outlive the function and allocates it on the heap instead of the stack. It's not undefined behavior, just potentially a bit more GC pressure than a stack allocation would have been.

**Q: Does `runtime.GC()` in production make things faster?**
A: Almost never — it forces an extra, blocking (from the caller's view) collection. It's a diagnostic/benchmarking tool, not a performance lever.

## System / Design Scenarios

**Q: A service's P99 latency spikes correlate with traffic bursts, though average CPU looks fine. How do you investigate?**
A: Enable `GODEBUG=gctrace=1` and correlate GC cycle frequency/CPU% with the burst timing; check `allocs/op` on the hot path via benchmarks; consider `sync.Pool` for hot-path buffers and `GOMEMLIMIT` to give the pacer more headroom.

**Q: How would you safely reduce a service's memory footprint in a container without risking more OOM kills?**
A: Set `GOMEMLIMIT` to roughly 80-90% of the container's hard memory limit rather than only tuning `GOGC`, so the GC becomes more aggressive as usage approaches the ceiling instead of waiting for the percentage-based trigger.

## Behavioral / Experience

**Q: Describe a time you diagnosed a performance issue down to the runtime level (GC, scheduler, allocation).**
A: (Tailor to experience — strong answers cite specific tools: `gctrace`, `pprof`, `-benchmem`, and describe the actual fix, e.g. pooling, reduced allocations, or a `GOMEMLIMIT`/`GOGC` change with measured before/after numbers.)

---

## Cheat Sheet

```
GMP            → Goroutine / Machine (OS thread) / Processor (GOMAXPROCS of them)
Escape analysis → stack (cheap) vs heap (GC-tracked) allocation decision
GOGC=100       → heap doubles before next GC
GOMEMLIMIT     → soft cap, GC works harder as usage approaches it
gctrace=1      → per-cycle GC stats: CPU%, heap before->peak->after, next goal
```

---

## Related Topics

- [Junior](junior.md) · [Middle](middle.md) · [Senior](senior.md) · [Professional](professional.md) · [Tasks](tasks.md)
