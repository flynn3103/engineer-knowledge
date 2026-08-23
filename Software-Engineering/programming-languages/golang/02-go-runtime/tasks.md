# Go Runtime — Hands-On Tasks

> **Topic:** [Go Runtime](../README.md)

---

## Warm-Up

1. Write two small functions, one whose local variable provably stays on the stack and one that forces a heap escape (e.g. by returning its address). Confirm with `go build -gcflags="-m"`.
2. Run any program with `GODEBUG=gctrace=1` and identify, from real output, the CPU%, heap-before, heap-after, and next-goal fields.

## Core

3. Write a benchmark (`testing.B`, `-benchmem`) for a function that allocates a new slice per call; record `allocs/op`. Refactor it to reuse a pre-allocated buffer and show the allocation count drop.
4. Build a small HTTP handler that allocates a `bytes.Buffer` per request; convert it to use `sync.Pool` and benchmark the difference under simulated concurrent load.
5. Run the same CPU-bound workload with `GOMAXPROCS(1)` and `GOMAXPROCS(runtime.NumCPU())`; measure wall-clock time for both and explain the difference in terms of parallelism vs. concurrency.

## Advanced

6. Reproduce a GC-pressure scenario: a program allocating heavily in a loop with `GOGC=400` vs. `GOGC=50`. Record total run time and peak memory (via `/usr/bin/time -v` or equivalent) for both and explain the trade-off you observe.
7. Set `GOMEMLIMIT` below a workload's natural peak heap size and observe (via `gctrace=1`) the GC running more aggressively as it approaches the limit, rather than waiting for the `GOGC` ratio to trigger.
8. Use `GODEBUG=schedtrace=1000` on a program with an intentionally unbalanced workload (e.g. one goroutine doing far more work than others) and observe the per-P run-queue numbers.

## Capstone

9. Take a hot function from any personal project (or a synthetic one), profile its `allocs/op` with `-benchmem`, and iteratively reduce allocations (buffer reuse, avoiding unnecessary `interface{}` boxing, avoiding string concatenation in a loop) until you've cut allocations by at least 50%. Document the before/after numbers and which change contributed most.

## If you can do all of these, you have the middle level

You can read escape-analysis output, interpret `gctrace`/`schedtrace`, and turn an allocation-heavy hot path into a measurably leaner one using real before/after benchmark numbers — not guesses.

---

## Related Topics

- [Junior](junior.md) · [Middle](middle.md) · [Senior](senior.md) · [Professional](professional.md) · [Interview](interview.md)
