# Go Runtime — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Go Runtime** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
---

## Core Concepts

### 1. Allocation rate, not heap size, usually drives GC cost

Two services with the same heap size can have wildly different GC overhead if one allocates 10x more short-lived garbage per request. GC cost scales primarily with *how much you allocate between cycles*, not how much you currently hold. Reducing allocations in hot paths (reusing buffers, avoiding unnecessary boxing/interface conversions, batching) is usually a bigger win than tuning `GOGC`.

### 2. `GOMEMLIMIT` changes GC behavior under memory pressure

Before Go 1.19, `GOGC` was the only lever, and a service near a container's memory limit could still get OOM-killed because the GC hadn't triggered yet by its percentage-based heuristic. `GOMEMLIMIT` sets a soft cap; as usage approaches it, the GC runs more aggressively (trading CPU for headroom) rather than waiting for the `GOGC` ratio to trigger. Setting it to ~80–90% of the container's hard memory limit is a common, safer default than relying on `GOGC` alone in constrained environments.

### 3. GC pacing interacts with latency, not just throughput

The GC's pacer tries to finish a mark cycle before the heap hits the goal size, using an estimate of allocation rate. A sudden burst of allocation (a traffic spike, a large batch job) can outrun the pacer's estimate, forcing the GC to slow down (or even briefly stop) mutator goroutines to keep up — this shows up as latency spikes correlated with traffic bursts, not steady-state load.

### 4. Escape analysis regressions are a real, recurring production issue

A refactor that changes how a function is called (passing through an `interface{}`/`any`, capturing a variable in a closure that's stored somewhere, returning a pointer instead of a value) can silently move allocations from stack to heap. This is invisible in a code review unless someone runs `-gcflags="-m"` or notices an allocation-count regression in a benchmark. Treat allocation benchmarks (`testing.B` with `-benchmem`) as a regression gate for hot paths, the same way you'd gate on correctness.

### 5. `sync.Pool` reduces allocation pressure for short-lived, reusable objects

```go
var bufPool = sync.Pool{New: func() any { return new(bytes.Buffer) }}

func handle() {
    buf := bufPool.Get().(*bytes.Buffer)
    defer func() { buf.Reset(); bufPool.Put(buf) }()
    // use buf
}
```

`sync.Pool` objects can be reclaimed by the GC at any time (they are *not* a cache with guaranteed retention), so it's a tool for reducing allocation churn under load, not a correctness-critical cache.

---

## Worked Example — Latency Spikes Traced to GC Pacing Under Bursty Traffic

A service showed P99 latency spikes of 300ms, exactly correlated with traffic bursts from a batch upstream client, despite average CPU usage looking fine. `gctrace=1` output during a spike showed multiple GC cycles firing in quick succession with the "CPU %" field jumping well above steady-state. The root cause: a hot path allocated a new slice per request instead of reusing a buffer, and burst traffic multiplied the allocation rate faster than the GC pacer's steady-state estimate accounted for. The fix combined two changes: a `sync.Pool` for the per-request buffer (cutting allocation rate substantially) and setting `GOMEMLIMIT` to give the pacer more headroom to avoid over-correcting during bursts.

---

## Code Examples

### Example 1 — Allocation benchmarking as a regression gate

```go
func BenchmarkHandler(b *testing.B) {
    b.ReportAllocs()
    for i := 0; i < b.N; i++ {
        handle(req)
    }
}
```

```bash
go test -bench=Handler -benchmem
BenchmarkHandler-8   500000   2453 ns/op   128 B/op   2 allocs/op
```

A jump in `allocs/op` between commits, with no logic change, is the signature of an escape-analysis regression.

### Example 2 — `GOMEMLIMIT` as a safety net

```bash
GOMEMLIMIT=1800MiB ./myservice   # container hard limit: 2GiB
```

---

## Best Practices

1. Gate hot-path benchmarks on `allocs/op`, not just `ns/op`.
2. Set `GOMEMLIMIT` in any containerized deployment with a hard memory limit.
3. Reach for `sync.Pool` only after profiling shows allocation churn is the actual bottleneck.
4. Correlate GC trace spikes with traffic patterns, not just wall-clock time, when diagnosing latency.

---

## Edge Cases & Pitfalls

- **`sync.Pool` items can vanish between GC cycles** — never rely on it for anything beyond a performance optimization; always handle a fresh allocation as the fallback.
- **`GOMEMLIMIT` set too close to the hard limit** leaves no room for the GC's own overhead and can cause thrashing (constant aggressive GC, high CPU, little forward progress).
- **A benchmark run on a different machine/Go version** can show different escape-analysis decisions — pin CI benchmark comparisons to consistent environments.

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| Tuning `GOGC` without a benchmark showing GC is the bottleneck | Profile with `pprof` and `gctrace` first |
| Using `sync.Pool` for correctness (e.g., connection reuse guarantees) | Use a real pool (e.g., `database/sql`'s connection pool) for anything requiring guaranteed retention |
| Ignoring `allocs/op` regressions in code review | Add `-benchmem` output to CI for hot-path packages |

---

## Tricky Points

- Lowering allocation rate can sometimes *increase* peak memory briefly (pooled objects held longer) even as it reduces total GC CPU time — measure both together.
- `GOMEMLIMIT` and `GOGC` interact: `GOMEMLIMIT` acts as an upper bound override on top of whatever `GOGC`'s ratio would otherwise allow.

---

## Apply it

1. State the system invariant that **Go Runtime** must protect.
2. Mark ownership, state, and failure propagation at each boundary.
3. Compare two designs under load, dependency failure, and future change.
4. Define recovery and compatibility behavior before implementation.
5. Test the riskiest assumption with a focused experiment.

## Verify your work

- The experiment supports the design with evidence, not preference.
- Failure injection shows the blast radius and recovery path.
- Compatibility checks cover old and new callers or data.
- Operational signals reveal invariant violations and recovery progress.

## Review questions

- Which invariant must remain true when Go Runtime fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
