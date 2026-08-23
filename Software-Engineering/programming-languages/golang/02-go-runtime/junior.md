# Go Runtime — Junior Level

> **Topic:** [Go Runtime](../README.md)
> **Focus:** What the Go runtime actually does for you — the scheduler, the garbage collector, growable stacks — and why "simple" Go code isn't running directly on the CPU the way C does.

---

## Introduction

Every compiled Go binary embeds a **runtime**: a piece of software that ships inside your program and handles goroutine scheduling, memory allocation, garbage collection, and growing stacks. You never call it directly, but almost everything interesting about Go's performance and behavior under load comes from understanding what it's doing behind your back.

Three runtime subsystems matter most day to day:

1. The **scheduler** — decides which goroutine runs on which OS thread, when.
2. The **garbage collector (GC)** — reclaims memory for values nothing references anymore.
3. **Stack management** — each goroutine's stack starts tiny (2 KB) and grows automatically.

---

## Prerequisites

- Comfortable with goroutines (see [Goroutines and Concurrency](../01-goroutines-and-concurrency/junior.md)).
- No prior runtime/GC knowledge required.

---

## Glossary

| Term | Definition |
|------|-----------|
| **Runtime** | The Go support library, linked into every binary, providing scheduling, GC, memory allocation. |
| **GMP model** | Goroutine / Machine (OS thread) / Processor — the scheduler's three core abstractions. |
| **`GOMAXPROCS`** | Max number of OS threads simultaneously executing Go code. Defaults to CPU core count. |
| **Garbage collector (GC)** | Automatically frees memory for objects no longer reachable from any live reference. |
| **Stop-the-world (STW)** | A brief pause where all goroutines halt so the GC can do bookkeeping safely. Go's STW pauses are typically sub-millisecond. |
| **Escape analysis** | Compile-time decision of whether a value can live on the stack or must be allocated on the heap. |
| **Stack growth** | A goroutine's stack starts at 2 KB and the runtime copies it to a larger buffer automatically when it fills up. |
| **`GOGC`** | Environment variable controlling how much the heap can grow between GC cycles before the next one triggers (default 100 = double). |
| **Allocation** | Reserving memory for a value, either on the stack (cheap, automatic) or the heap (tracked by the GC). |

---

## Core Concepts

### 1. The runtime is not the operating system

When you write `go f()`, you are not asking the OS for a thread. You are handing the Go runtime's scheduler a unit of work, which it places onto one of a small number of OS threads it manages (`GOMAXPROCS` many, by default). This indirection is what makes goroutines cheap.

### 2. The GC runs concurrently, mostly

Go's garbage collector runs *alongside* your program most of the time (concurrent mark-and-sweep), pausing everything only for very short "stop-the-world" phases (typically under a millisecond) to coordinate. This is why Go programs don't usually see the multi-second GC pauses associated with older Java collectors — but GC still costs CPU time, taken away from your program's own work.

### 3. Stacks grow, they don't overflow (usually)

A new goroutine's stack is tiny — about 2 KB. If a function call needs more room than remains, the runtime allocates a bigger stack (roughly double), copies everything over, and fixes up all pointers into the old stack. This is transparent to your code, but it's not free — it's a stop-the-world-adjacent, though very fast, operation per goroutine.

### 4. Escape analysis decides stack vs. heap

```go
func onStack() int {
    x := 5
    return x // x's value is copied out; x itself never escapes
}
func onHeap() *int {
    x := 5
    return &x // x's address escapes the function; it must live on the heap
}
```

The compiler decides this at compile time. Stack allocation is essentially free (bump a pointer, no GC involvement); heap allocation costs more and adds GC pressure. You can see the compiler's decisions with `go build -gcflags="-m"`.

### 5. `GOGC` controls the memory/CPU trade-off

The default `GOGC=100` means: let the heap double before the next GC cycle. Lower it and GC runs more often (less peak memory, more CPU spent collecting); raise it and GC runs less often (more peak memory, less CPU spent collecting). `GOMEMLIMIT` (Go 1.19+) sets a hard memory ceiling the GC will work harder to respect.

### 6. Simple code, non-simple runtime behavior

The same loop can allocate zero, some, or a lot of garbage depending on whether values escape to the heap — which itself can change based on how a function is called elsewhere, inlining decisions, or a seemingly unrelated refactor. This is why "why did this get slower" in Go often traces back to an escape-analysis change, not a logic change.

---

## Code Examples

### Example 1 — Seeing escape analysis decisions

```bash
$ go build -gcflags="-m" main.go
./main.go:6:2: moved to heap: x
```

### Example 2 — Measuring GC pause impact

```go
var stats debug.GCStats
debug.ReadGCStats(&stats)
fmt.Println("num GC:", stats.NumGC, "total pause:", stats.PauseTotal)
```

### Example 3 — Setting `GOGC` and `GOMEMLIMIT`

```bash
GOGC=50 GOMEMLIMIT=512MiB ./myservice
```

Lowers the heap-growth threshold and sets a soft memory ceiling — useful in memory-constrained containers.

---

## Pros & Cons

| | Pros | Cons |
|---|---|---|
| **Automatic GC** | No manual `free()`, no use-after-free bugs | Uses CPU cycles you don't directly control; tuning is indirect (`GOGC`, `GOMEMLIMIT`) |
| **Growable stacks** | Goroutines can start tiny and cheap | Stack-growth copies happen transparently and can show up in profiles as unexpected cost |
| **M:N scheduler** | Massive goroutine counts on few OS threads | Scheduling decisions are mostly opaque; deep tuning needs `GODEBUG` and trace tools |

---

## Use Cases

| Situation | What to know |
|---|---|
| Service is CPU-bound and GC shows up in profiles | Consider raising `GOGC` if memory headroom allows |
| Service runs in a memory-constrained container | Set `GOMEMLIMIT` to avoid OOM kills from GC lagging behind allocation |
| Code allocates more than expected | Check escape analysis (`-gcflags="-m"`) for values unexpectedly moved to the heap |

---

## Best Practices

1. Don't tune `GOGC`/`GOMEMLIMIT` without a profile showing GC is actually the bottleneck.
2. Set `GOMAXPROCS` explicitly (or use `automaxprocs`) inside containers with a CPU quota.
3. Treat unexpected heap escapes as a signal, not noise — sometimes a tiny refactor (returning a value instead of a pointer) removes real allocation pressure.
4. Use `GOMEMLIMIT` in memory-constrained environments to avoid OOM kills.

---

## Edge Cases & Pitfalls

- **A goroutine leak is also a memory leak from the GC's perspective** — the GC can't collect memory a still-live goroutine is holding, no matter how aggressively it runs.
- **Lowering `GOGC` too far trades memory for CPU** you may not have spare.
- **`GOMAXPROCS` set higher than actual CPU quota** in a container causes scheduler overhead without any real parallelism gain.

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| Assuming Go has "no GC pauses" | It has very short concurrent-phase pauses, not zero — measure, don't assume |
| Tuning `GOGC` blindly to "fix performance" | Profile first (`pprof`) — GC might not be the actual bottleneck |
| Ignoring container CPU quotas | Set `GOMAXPROCS` explicitly or use `automaxprocs` |

---

## Cheat Sheet

```
GOMAXPROCS   — max OS threads running Go code concurrently (default: CPU count)
GOGC         — heap growth % before next GC (default 100 = double)
GOMEMLIMIT   — soft memory ceiling (Go 1.19+)
go build -gcflags="-m"   — show escape analysis decisions
```

---

## Summary

- The Go runtime schedules goroutines onto OS threads (GMP model), manages a concurrent garbage collector, and grows goroutine stacks automatically.
- The GC runs mostly concurrently with very short stop-the-world pauses, but still consumes CPU.
- Escape analysis decides stack vs. heap allocation at compile time — visible via `-gcflags="-m"`.
- `GOGC` and `GOMEMLIMIT` are the main levers for trading memory against CPU spent on GC.
- Set `GOMAXPROCS` deliberately in containers.

---

## Further Reading

- The Go Blog — *Getting to Go: The Journey of Go's Garbage Collector*: <https://go.dev/blog/ismmkeynote>
- A Guide to the Go Garbage Collector (official docs): <https://go.dev/doc/gc-guide>

---

## Related Topics

- [Goroutines and Concurrency](../01-goroutines-and-concurrency/junior.md) — what the scheduler is scheduling.
- [Production Debugging](../07-production-debugging/junior.md) — profiling GC and allocation with `pprof`.
