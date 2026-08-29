# Goroutines and Concurrency — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Goroutines and Concurrency** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
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

## Apply it

1. Find a real component where **Goroutines and Concurrency** affects an interface or dependency.
2. Write two plausible choices and the constraint that favors each one.
3. Make the smallest reversible change at that boundary.
4. Exercise the component alone, then exercise the integrated flow.
5. Keep the decision note with the evidence that selected the option.

## Verify your work

- A focused check proves the local behavior.
- An integrated check proves callers and dependencies still agree.
- Logs, traces, compiler output, or benchmarks expose the boundary.
- Reverting the change restores the previous behavior without unrelated edits.

## Review questions

- Which boundary is most affected by Goroutines and Concurrency?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
