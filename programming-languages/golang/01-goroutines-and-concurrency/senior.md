# Goroutines and Concurrency — Senior

> **Topic:** [Goroutines and Concurrency](../README.md)
> **Focus:** Goroutine-leak detection at scale, `GOMAXPROCS` and scheduler tuning, lock-free patterns with `atomic`, structuring cancellation across a fleet, and designing concurrency into a service rather than bolting it on.

---

## Introduction

Correct concurrent code that works in a unit test can still degrade a production service: a goroutine count that only ever grows, a mutex that becomes a bottleneck at 10x traffic, a deadlock that only manifests under a specific interleaving that CI never hits. At senior level the job shifts from "write correct concurrent code" to "design a system whose concurrency is observable, bounded, and recoverable."

---

## Prerequisites

- Comfortable with `errgroup`, pipelines, mutexes vs. channels, and the race detector (middle level).

---

## Core Concepts

### 1. Goroutine leaks are a slow-motion outage

A leaked goroutine costs its stack (grows from 2 KB), whatever it's holding (a DB connection, an open file, a captured request), and — critically — it's invisible until `runtime.NumGoroutine()` or a memory graph shows a line going up and to the right forever. The fix is always structural: every goroutine must have a reachable, guaranteed exit path (a closed channel, a canceled context, a bounded loop) — "it'll probably finish eventually" is not an exit path.

### 2. `GOMAXPROCS` matters more in containers than people expect

`GOMAXPROCS` defaults to the number of logical CPUs the Go runtime detects, which historically meant the **host's** CPU count — even inside a container with a much smaller CPU quota. Running with `GOMAXPROCS` higher than your actual CPU allotment causes excessive context switching and scheduler overhead. Set it explicitly, or use `go.uber.org/automaxprocs` to read the cgroup quota automatically.

### 3. `sync/atomic` for the smallest critical sections

```go
var counter atomic.Int64
counter.Add(1)
n := counter.Load()
```

For a single counter, `atomic` avoids the overhead of lock/unlock entirely. It does **not** generalize to protecting multiple related fields — the moment you need to update two things together, you need a mutex (or a redesign) so the update is atomic as a whole, not just each field individually.

### 4. Cancellation must be designed at the boundary, not sprinkled inside

A large system should have one place per request/job where a `context.Context` with a deadline is created (the HTTP handler, the queue consumer) and that same context threaded through every downstream call. Retrofitting cancellation into a codebase that never threaded `context` from the start usually means every function signature needs to change — plan for it up front.

### 5. Bounding concurrency system-wide, not just per-function

A worker pool inside one function bounds *that* function's concurrency, but ten call sites each spawning "just a few" unbounded goroutines can still sum to resource exhaustion. At scale, concurrency limits belong in shared infrastructure — a global semaphore, a rate limiter, or a fixed-size dispatcher — not scattered as local decisions.

### 6. Detecting leaks before they page someone

- `runtime.NumGoroutine()` exported as a metric, alert on sustained growth.
- `pprof`'s goroutine profile (`/debug/pprof/goroutine?debug=2`) shows every goroutine's stack — group by stack trace to find *which* code path is leaking.
- `go.uber.org/goleak` in tests: fails a test if goroutines it started are still running when it ends.

---

## Code Examples

### Example 1 — `goleak` in a test

```go
func TestMain(m *testing.M) {
    goleak.VerifyTestMain(m)
}
```

Any test in the package that leaves a goroutine running after it finishes now fails the build, instead of quietly accumulating leaks that only show up in production.

### Example 2 — Bounded, cancelable dispatcher

```go
type Dispatcher struct {
    sem chan struct{}
}
func NewDispatcher(n int) *Dispatcher { return &Dispatcher{sem: make(chan struct{}, n)} }

func (d *Dispatcher) Run(ctx context.Context, fn func(context.Context) error) error {
    select {
    case d.sem <- struct{}{}:
    case <-ctx.Done():
        return ctx.Err()
    }
    defer func() { <-d.sem }()
    return fn(ctx)
}
```

A single shared `Dispatcher` used across every call site in the service gives one place to change the global concurrency budget.

### Example 3 — `automaxprocs`

```go
import _ "go.uber.org/automaxprocs"

func main() {
    // GOMAXPROCS is now set to match the container's CPU quota automatically
}
```

---

## Worked Example — A Slow Memory Leak Traced to a Forgotten `context`

A background sync job spawned one goroutine per item, each opening a gRPC stream with no deadline. Under normal load, streams closed quickly and nobody noticed. During a partial outage of a downstream service, streams started hanging indefinitely — no timeout meant no automatic cleanup. Goroutine count climbed from ~200 to ~40,000 over six hours before memory pressure triggered OOM kills. The `pprof` goroutine profile showed forty thousand identical stacks blocked in the same `stream.Recv()` call. The fix: every stream got a `context.WithTimeout`, and the dispatcher above capped total concurrent streams regardless of downstream health.

---

## Pros & Cons

| Approach | Pros | Cons |
|---|---|---|
| `sync/atomic` | Fastest option for single counters, no lock contention | Doesn't generalize to multi-field invariants |
| Global dispatcher/semaphore | One place to reason about total concurrency | A single bottleneck if sized wrong; must be shared correctly across goroutines |
| `goleak` in CI | Catches leaks before they reach production | Only catches leaks the test suite actually exercises |

---

## Best Practices

1. Every goroutine gets a deadline or a cancellation path before it's allowed to touch a network call.
2. Export `runtime.NumGoroutine()` as a metric and alert on trend, not just absolute value.
3. Set `GOMAXPROCS` deliberately in containerized environments.
4. Add `goleak.VerifyTestMain` to packages that spawn goroutines.
5. Centralize concurrency limits rather than letting every call site invent its own.

---

## Edge Cases & Pitfalls

- **A context timeout doesn't cancel work already inside a blocking syscall** that isn't context-aware (e.g. some C bindings) — the goroutine can still hang past the deadline.
- **`atomic` operations on a struct field accessed both atomically and non-atomically elsewhere** is still a race — every access to that field must go through `atomic`.
- **A dispatcher's semaphore sized for steady state can starve everyone during a burst** — decide explicitly whether bursts should queue, shed load, or borrow capacity.

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| No timeout on a network call inside a goroutine | Always derive a `context.WithTimeout` before the call |
| Sizing a global semaphore once and never revisiting it | Tie it to measured resource limits (DB connections, CPU, memory) and review under load testing |
| Treating `NumGoroutine` spikes as "probably fine" | Any sustained upward trend is a leak until proven otherwise |

---

## Tricky Points

- A goroutine blocked on a channel with no timeout is functionally identical, from a leak-detection standpoint, to one blocked on a hung network call — both need an escape hatch.
- Raising `GOMAXPROCS` does not reduce contention on a mutex-protected resource; it can make it worse by increasing the number of goroutines competing for the same lock.

---

## Cheat Sheet

```go
// Global bounded dispatcher
d := NewDispatcher(50)
err := d.Run(ctx, func(ctx context.Context) error { return doWork(ctx) })

// Leak detection in tests
func TestMain(m *testing.M) { goleak.VerifyTestMain(m) }

// CPU-aware GOMAXPROCS
import _ "go.uber.org/automaxprocs"
```

---

## Summary

- Goroutine leaks are silent until they aren't — instrument `NumGoroutine`, use `pprof`'s goroutine profile, and add `goleak` to tests.
- `GOMAXPROCS` should match the actual CPU quota, especially in containers.
- `atomic` is for single values; anything with multi-field invariants needs a mutex.
- Concurrency limits belong in shared, centralized infrastructure, not ad hoc per-call-site decisions.
- Every network call inside a goroutine needs a deadline; "it'll probably come back" is how leaks are born.

---

## Further Reading

- `go.uber.org/goleak`: <https://pkg.go.dev/go.uber.org/goleak>
- `go.uber.org/automaxprocs`: <https://pkg.go.dev/go.uber.org/automaxprocs>
- The Go Blog — *Introducing the Go Race Detector*: <https://go.dev/blog/race-detector>

---

## Related Topics

- [Go Runtime](../02-go-runtime/senior.md) — the scheduler and GC behavior underneath these decisions.
- [Production Debugging](../07-production-debugging/senior.md) — using `pprof`'s goroutine profile in anger.

---

## Check your understanding

1. Explain Goroutines and Concurrency — Senior Level in your own words and name the problem it solves.
2. How would you apply the ideas around Introduction, Prerequisites, Core Concepts in a realistic engineering change?
3. What failure mode or misuse should you look for, and what evidence would reveal it?
4. How would you validate a system-level decision about Goroutines and Concurrency — Senior Level under uncertainty?
5. What observable result would convince you that the approach improved the system?
