# Goroutines and Concurrency — Middle Level

> **Topic:** [Goroutines and Concurrency](../README.md)
> **Focus:** `errgroup`, pipelines, `sync.Mutex` vs channels, the race detector, `context` propagation, and preventing leaks by design.

---

## Introduction

At the junior level you learned to spawn, wait, and pass values through channels. At this level the questions get sharper: how do you propagate an **error** out of a group of goroutines? How do you build a multi-stage **pipeline**? When should you reach for a `sync.Mutex` instead of a channel? And how do you stop writing code that merely *works* and start writing code that provably doesn't race or leak?

---

## Prerequisites

- Comfortable with goroutines, `WaitGroup`, unbuffered/buffered channels, and `select` (junior level).
- Basic familiarity with `context.Context`.

---

## Glossary

| Term | Definition |
|------|-----------|
| **`errgroup.Group`** | `golang.org/x/sync/errgroup` — like `WaitGroup` but propagates the first error and can cancel a shared `context` on failure. |
| **Pipeline** | A chain of stages, each a goroutine, connected by channels, where each stage transforms values from the previous one. |
| **`sync.Mutex`** | A mutual-exclusion lock protecting a critical section of shared memory. |
| **`sync.RWMutex`** | A lock allowing many concurrent readers or one writer. |
| **Data race** | Two goroutines accessing the same memory location concurrently, with at least one write, and no synchronization — undefined behavior in Go. |
| **`-race`** | The Go race detector, a compile-time instrumentation flag (`go test -race`, `go run -race`). |
| **Context tree** | The parent/child hierarchy formed by `context.WithCancel`/`WithTimeout` — canceling a parent cancels every descendant. |
| **Backpressure** | Slowing a fast producer down to match a slower consumer, usually via a bounded buffered channel. |
| **`or-done` channel** | A wrapper pattern that makes a channel read also respect a `context`'s cancellation. |

---

## Core Concepts

### 1. `errgroup` is `WaitGroup` with error propagation

```go
g, ctx := errgroup.WithContext(context.Background())
for _, url := range urls {
    url := url
    g.Go(func() error {
        return fetch(ctx, url)
    })
}
if err := g.Wait(); err != nil {
    return err
}
```

The moment any `g.Go` function returns a non-nil error, `ctx` is canceled — every other in-flight goroutine that respects `ctx.Done()` can stop early instead of finishing wasted work. `g.Wait()` returns the *first* error.

### 2. Channel vs mutex is a design choice, not a religion

Rule of thumb: use a **channel** when you're handing *ownership* of a value from one goroutine to another (a pipeline stage, a result). Use a **mutex** when multiple goroutines need to read/modify a small piece of *shared state* in place (a counter, a cache map) and passing ownership around would be awkward.

```go
type SafeCounter struct {
    mu sync.Mutex
    n  int
}
func (c *SafeCounter) Inc() {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.n++
}
```

Trying to model a shared counter with channels (a goroutine "owning" the counter, others sending it increment requests) is possible but usually more code for no benefit.

### 3. Pipelines compose

```go
func gen(nums ...int) <-chan int {
    out := make(chan int)
    go func() { defer close(out); for _, n := range nums { out <- n } }()
    return out
}
func square(in <-chan int) <-chan int {
    out := make(chan int)
    go func() { defer close(out); for n := range in { out <- n * n } }()
    return out
}
// usage
for v := range square(gen(1, 2, 3, 4)) {
    fmt.Println(v)
}
```

Each stage owns its output channel and closes it when done, which is what lets downstream `range` loops terminate. Composition is just function calls.

### 4. The race detector finds races you can't see by testing

A race can be present in code that "works" a thousand test runs in a row and only misbehaves under specific scheduling. `go test -race ./...` instruments every memory access and reports the two goroutines and stack traces involved the moment a race actually occurs during that run — it does not prove absence of races, only presence during the run it observed. Run it in CI, always, not just locally.

### 5. Context cancellation must be checked, not assumed

Passing a `context.Context` down a call chain does nothing by itself — every goroutine that can block must explicitly select on `ctx.Done()`:

```go
select {
case <-ctx.Done():
    return ctx.Err()
case result <- compute():
}
```

A goroutine that ignores `ctx` and blocks on a channel forever is a leak *even if the caller canceled the context* — cancellation is cooperative, not preemptive.

### 6. Backpressure via bounded channels

```go
sem := make(chan struct{}, 10) // at most 10 concurrent
for _, item := range items {
    sem <- struct{}{}
    go func(item Item) {
        defer func() { <-sem }()
        process(item)
    }(item)
}
```

A buffered channel used purely for its capacity — a **semaphore** — is a standard way to cap how much concurrent work is in flight without a full worker-pool rewrite.

---

## Code Examples

### Example 1 — `errgroup` with bounded concurrency (`SetLimit`)

```go
g, ctx := errgroup.WithContext(context.Background())
g.SetLimit(8) // at most 8 concurrent Go calls
for _, id := range ids {
    id := id
    g.Go(func() error {
        return fetchAndStore(ctx, id)
    })
}
return g.Wait()
```

`SetLimit` (Go 1.20+) turns `errgroup` into a bounded worker pool with error propagation built in — no manual semaphore needed.

### Example 2 — `or-done` channel wrapper

```go
func orDone(ctx context.Context, c <-chan int) <-chan int {
    out := make(chan int)
    go func() {
        defer close(out)
        for {
            select {
            case <-ctx.Done():
                return
            case v, ok := <-c:
                if !ok {
                    return
                }
                select {
                case out <- v:
                case <-ctx.Done():
                    return
                }
            }
        }
    }()
    return out
}
```

Wrapping every pipeline read with `orDone` means canceling the top-level `context` unblocks every stage, instead of only the ones that happen to check `ctx.Done()` directly.

### Example 3 — `RWMutex` for a read-heavy cache

```go
type Cache struct {
    mu   sync.RWMutex
    data map[string]string
}
func (c *Cache) Get(k string) (string, bool) {
    c.mu.RLock()
    defer c.mu.RUnlock()
    v, ok := c.data[k]
    return v, ok
}
func (c *Cache) Set(k, v string) {
    c.mu.Lock()
    defer c.mu.Unlock()
    c.data[k] = v
}
```

Many readers can hold `RLock` simultaneously; a writer needs exclusive `Lock`. Worth it only when reads vastly outnumber writes — `RWMutex` has more overhead per lock than `Mutex` under low contention.

---

## Pros & Cons

| Approach | Pros | Cons |
|---|---|---|
| `errgroup` | First-error propagation, automatic cancellation, `SetLimit` bounding | Pulls in `golang.org/x/sync`; only the *first* error is kept |
| `sync.Mutex`/`RWMutex` | Simple, fast for small critical sections | Easy to forget to unlock, easy to hold too long, doesn't compose with `select` |
| Pipelines | Naturally streaming, backpressure-friendly, composable | More boilerplate than a single loop for simple cases |

---

## Use Cases

| Situation | Tool |
|---|---|
| Call 20 services in parallel, fail fast on first error | `errgroup.WithContext` |
| Protect an in-memory counter/cache from concurrent access | `sync.Mutex` / `sync.RWMutex` |
| Stream and transform a large dataset without loading it all into memory | Pipeline of channel-connected stages |
| Cap "at most N in flight" without a fixed worker count | Buffered channel used as a semaphore, or `errgroup.SetLimit` |

---

## Coding Patterns

- **Cancel-on-first-error**: `errgroup.WithContext` — the idiomatic replacement for hand-rolled "send error to a channel, close done" code.
- **or-done wrapping**: every channel read in a pipeline goes through a helper that also selects on `ctx.Done()`.
- **Bounded fan-out**: a semaphore channel or `errgroup.SetLimit` caps concurrent goroutines regardless of input size.

---

## Best Practices

1. Prefer `errgroup` over manual `WaitGroup` + error channel when any goroutine can fail.
2. Keep critical sections under a mutex as short as possible — never call another goroutine's code (which might also lock) while holding a lock.
3. Every pipeline stage closes the channel it owns, and only that one.
4. Run `-race` in CI on every PR, not just before releases.
5. Thread a single `context.Context` through an entire request/job, don't create ad hoc ones per function.

---

## Edge Cases & Pitfalls

- **Holding a lock while calling out to slow I/O** serializes what should be concurrent work — release the lock before the slow call if possible.
- **`errgroup.Wait()` only returns the first error** — others are dropped unless you collect them yourself.
- **A semaphore channel that's never drained on the error path** (e.g. a `panic` before `<-sem`) leaks capacity — always `defer` the release.
- **Copying a `sync.Mutex`** (e.g. passing a struct containing one by value) is a bug the compiler won't catch but `go vet` will.

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| Ignoring `errgroup`'s returned `ctx` in child goroutines | Pass that `ctx`, not the original, into every `g.Go` closure |
| Locking a mutex, then calling a function that also tries to lock it | Reentrant locking deadlocks in Go — restructure so nested calls don't re-lock |
| Building a pipeline where a middle stage doesn't close its output on early return | Always `defer close(out)` right after creating the channel |

---

## Tricky Points

- `errgroup`'s `ctx` is **derived from**, not identical to, the one you passed to `WithContext` — cancel propagates parent → child, never the reverse.
- A `sync.RWMutex` writer can starve under continuous read pressure on some implementations; Go's does bias toward writers to avoid this, but it's not instantaneous.
- `select` with a `default` case never blocks — useful for a non-blocking send/receive, easy to misuse into a busy-loop if you forget to also block somewhere.

---

## Cheat Sheet

```go
g, ctx := errgroup.WithContext(context.Background())
g.SetLimit(n)
g.Go(func() error { return work(ctx) })
err := g.Wait()

var mu sync.RWMutex
mu.RLock(); defer mu.RUnlock()   // reads
mu.Lock();  defer mu.Unlock()    // writes

go test -race ./...
```

---

## Summary

- `errgroup` is the idiomatic upgrade from `WaitGroup` when goroutines can fail: first-error propagation plus automatic cancellation.
- Choose channels for handing off ownership of values; choose mutexes for protecting small pieces of shared state in place.
- Pipelines compose from simple channel-owning stages; always close what you own.
- The race detector (`-race`) belongs in CI on every run, not as an occasional check.
- Context cancellation is cooperative — every blocking select must explicitly watch `ctx.Done()`.

---

## Further Reading

- `golang.org/x/sync/errgroup` docs: <https://pkg.go.dev/golang.org/x/sync/errgroup>
- The Go Blog — *Pipelines and Cancellation*: <https://go.dev/blog/pipelines>
- The Go Blog — *Go Concurrency Patterns: Context*: <https://go.dev/blog/context>

---

## Related Topics

- [Goroutines and Concurrency — Junior](junior.md) — the fundamentals this page builds on.
- [Production Debugging](../07-production-debugging/junior.md) — using `-race` and `pprof` together in CI.
