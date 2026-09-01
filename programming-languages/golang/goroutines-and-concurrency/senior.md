# Goroutines and Concurrency — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Goroutines and Concurrency** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
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

## Apply it

1. State the system invariant that **Goroutines and Concurrency** must protect.
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

- Which invariant must remain true when Goroutines and Concurrency fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
