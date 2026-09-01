# Go Runtime — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Go Runtime** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
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

## Apply it

1. Choose one small, known input for **Go Runtime**.
2. Predict the output or observable behavior.
3. Run the smallest example or probe that exercises the concept.
4. Change one input to trigger a failure or boundary case.
5. Explain the evidence using the guide's vocabulary.

## Verify your work

- Record the exact input, command or code path, and output.
- Repeat the probe and confirm the result is consistent.
- Show one expected success and one expected failure.
- Resolve any difference between the prediction and the evidence.

## Review questions

- What problem does Go Runtime solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
