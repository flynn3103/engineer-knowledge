# Goroutines and Concurrency — Junior

> **Topic:** [Goroutines and Concurrency](../README.md)
> **Focus:** Starting goroutines, waiting for them correctly, the two channel flavors, a first worker pool, and the loop-variable bug everyone hits once.

---

## Introduction

A **goroutine** is a function running independently of the code that started it. You get one by writing `go` in front of a function call:

```go
go doWork()
```

The Go runtime multiplexes many goroutines (thousands, even millions) onto a small pool of OS threads. Goroutines start cheap — about 2 KB of stack — and grow only if they need to. That cheapness is what makes Go's "just spawn a goroutine" style practical where other languages need thread pools and careful budgeting.

A **channel** is how goroutines talk to each other safely, without touching the same memory directly:

```go
ch := make(chan int)
go func() { ch <- 42 }()
fmt.Println(<-ch) // 42
```

This page covers the minimum you need to write correct, non-leaking concurrent code: spawning and joining goroutines, buffered vs. unbuffered channels, a basic worker pool, and the classic first-week bugs (unwaited goroutines, captured loop variables, deadlocks).

---

## Prerequisites

- Comfortable writing and running a Go program (`go run`, functions, closures).
- Know what a function literal (`func() { ... }`) is.
- No prior concurrency experience required — this is the starting point.

---

## Glossary

| Term | Definition |
|------|-----------|
| **Goroutine** | A function executing concurrently with others, scheduled by the Go runtime, started with `go`. |
| **Channel** | A typed pipe for sending and receiving values between goroutines. |
| **Unbuffered channel** | A channel with capacity 0. A send blocks until a receiver is ready, and vice versa. |
| **Buffered channel** | A channel with capacity N. A send only blocks once N unreceived values are queued. |
| **`select`** | A statement that waits on multiple channel operations, proceeding with whichever is ready first. |
| **`sync.WaitGroup`** | A counter with `Add`/`Done`/`Wait`, used to wait for a group of goroutines to finish. |
| **Worker pool** | A fixed number of goroutines pulling work off a shared channel, bounding concurrency. |
| **Fan-out** | Distributing units of work across multiple goroutines. |
| **Fan-in** | Merging results from multiple goroutines into a single channel. |
| **Race condition** | Two goroutines accessing the same memory concurrently, at least one a write, without synchronization. |
| **Deadlock** | All goroutines are blocked waiting on each other; nothing can make progress. |
| **Goroutine leak** | A goroutine that never exits, holding memory/resources forever. |
| **`context.Context`** | A carrier for cancellation signals and deadlines, passed down a call chain. |

---

## Core Concepts

### 1. `main` doesn't wait for anyone

```go
func main() {
    go fmt.Println("from goroutine")
    fmt.Println("from main")
}
```

This almost always prints only `from main` — `main` returns and the program exits before the goroutine gets a turn. **Spawning a goroutine is not the same as running it to completion.** You must explicitly wait.

### 2. `sync.WaitGroup` is the simplest join

```go
var wg sync.WaitGroup
wg.Add(1)
go func() {
    defer wg.Done()
    fmt.Println("from goroutine")
}()
wg.Wait()
```

Call `Add` **before** `go`, in the parent — not inside the goroutine, or `Wait` can race ahead and return before the goroutine even starts.

### 3. Unbuffered channels synchronize; buffered channels queue

An unbuffered channel forces the sender and receiver to "meet" — the send blocks until someone is receiving. A buffered channel lets the sender get ahead by up to N items before it blocks. Use unbuffered when you need a handshake; use small buffers when you want to decouple producer speed from consumer speed without unbounded memory growth.

### 4. `select` waits on multiple channels

```go
select {
case v := <-ch1:
    fmt.Println("got", v)
case <-time.After(time.Second):
    fmt.Println("timed out")
}
```

`select` picks whichever case is ready. If several are ready at once, it picks one at random — never assume ordering.

### 5. Context carries cancellation, not data pipelines

```go
ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
defer cancel()
select {
case <-ctx.Done():
    return ctx.Err()
case v := <-work:
    return process(v)
}
```

`ctx.Done()` closes when the deadline passes or `cancel()` is called. Every goroutine that might run long should watch it.

### 6. A worker pool bounds concurrency

```go
jobs := make(chan int, 100)
var wg sync.WaitGroup
for w := 0; w < 4; w++ {
    wg.Add(1)
    go func() {
        defer wg.Done()
        for j := range jobs {
            process(j)
        }
    }()
}
for i := 0; i < 20; i++ {
    jobs <- i
}
close(jobs)
wg.Wait()
```

Closing `jobs` is what lets the `for range jobs` loops in each worker exit — without it, every worker blocks forever waiting for the next job. That's a leak.

---

## Code Examples

### Example 1 — Fan-out / fan-in

```go
func fanIn(chans ...<-chan int) <-chan int {
    out := make(chan int)
    var wg sync.WaitGroup
    wg.Add(len(chans))
    for _, c := range chans {
        go func(c <-chan int) {
            defer wg.Done()
            for v := range c {
                out <- v
            }
        }(c)
    }
    go func() {
        wg.Wait()
        close(out)
    }()
    return out
}
```

Each input channel gets its own goroutine copying values into `out`; a separate goroutine closes `out` once all copiers are done. This is the standard shape of fan-in.

### Example 2 — The captured loop variable

```go
for i := 0; i < 3; i++ {
    go func() { fmt.Println(i) }() // BUG on Go < 1.22
}
```

Before Go 1.22, every closure shares the same `i`; by the time the goroutines run, the loop has usually finished and `i == 3`. Fix (works on every version):

```go
for i := 0; i < 3; i++ {
    go func(i int) { fmt.Println(i) }(i)
}
```

Go 1.22+ gives each iteration its own `i` automatically, but writing the explicit parameter is still good practice for clarity and for code that must compile on older versions.

### Example 3 — A deadlock

```go
ch := make(chan int)
ch <- 1        // blocks forever: no one is receiving, and we're the only goroutine
fmt.Println(<-ch)
```

The runtime detects "all goroutines are asleep" and panics rather than hanging silently — a courtesy Go gives you that many languages don't.

---

## Pros & Cons

| | Pros | Cons |
|---|---|---|
| **Goroutines** | Cheap (~2 KB), simple `go f()` syntax, scale to hundreds of thousands | Easy to leak; an unrecovered panic kills the whole process |
| **Channels** | Safe communication without manual locking; compose naturally with `select` | Easy to deadlock; unbuffered channels need a careful sender/receiver dance |
| **Worker pools** | Bound memory and CPU under bursty load | Adds complexity versus a plain loop; sizing the pool is a judgment call |

---

## Use Cases

| Situation | Approach |
|---|---|
| Fetch N independent things in parallel | Spawn N goroutines, join with `WaitGroup` or `errgroup` |
| Unbounded stream of work items | Worker pool reading from a channel |
| "Whichever finishes first wins" | `select` across multiple channels |
| Must stop working when the caller gives up | `context.Context`, checked in every loop iteration |
| A single value, computed once, needed everywhere | Plain function call — no concurrency needed |

---

## Best Practices

1. Know how every goroutine you start will exit, before you start it.
2. Call `wg.Add()` in the parent, before `go`; `defer wg.Done()` inside.
3. Never use `time.Sleep` to "wait" for a goroutine — use `WaitGroup`, a channel, or `errgroup`.
4. Pass loop variables as parameters into closures.
5. Close a channel only from the sender side, and only once.
6. Always run `go test -race` in CI.
7. Give long-running goroutines a `context.Context` and check `ctx.Done()`.

---

## Edge Cases & Pitfalls

- **Sending on a closed channel panics.** Only the sender should close, and only once "no more sends" is guaranteed.
- **Receiving from a closed channel never blocks** — it returns the zero value immediately (`v, ok := <-ch` with `ok == false` distinguishes this from a real zero value).
- **A `nil` channel blocks forever** on both send and receive — sometimes used intentionally to disable a `select` case.
- **Unbuffered channel + no waiting goroutine on the other side = deadlock**, not a race.

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| Forgetting to `close(jobs)` in a worker pool | Workers block forever on `range jobs` — always close after the last send |
| `time.Sleep` instead of a real join | Use `WaitGroup` / channels |
| Capturing the loop variable | Pass it as a parameter |
| Unbuffered channel with only one goroutine | Always needs a matching sender **and** receiver, in different goroutines |

---

## Cheat Sheet

```go
// Spawn + wait
var wg sync.WaitGroup
wg.Add(1)
go func() { defer wg.Done(); work() }()
wg.Wait()

// Worker pool
jobs := make(chan Job, 100)
for i := 0; i < N; i++ {
    go func() { for j := range jobs { handle(j) } }()
}
close(jobs) // after all sends

// Select with timeout
select {
case v := <-ch:
    use(v)
case <-time.After(2 * time.Second):
    // timed out
}
```

---

## Summary

- A goroutine is `go f()`; it runs independently and `main` will not wait for it automatically.
- `sync.WaitGroup` is the simplest way to wait for a group of goroutines.
- Unbuffered channels synchronize; buffered channels queue up to a limit.
- `select` lets one goroutine react to whichever of several channels is ready first.
- Worker pools bound concurrency; always `close()` the job channel once, from the sender.
- The two beginner bugs to internalize: the captured loop variable, and forgetting to wait/close.

---

## Further Reading

- Effective Go — *Goroutines* and *Channels*: <https://go.dev/doc/effective_go>
- The Go Blog — *Share Memory By Communicating*: <https://go.dev/blog/codelab-share>
- *Go Concurrency Patterns* (Rob Pike): <https://www.youtube.com/watch?v=f6kdp27TYZs>

---

## Related Topics

- [Go Runtime](../02-go-runtime/junior.md) — what the scheduler is actually doing with all these goroutines.
- [Production Debugging](../07-production-debugging/junior.md) — finding goroutine leaks with `pprof`.

---

## Check your understanding

1. Explain Goroutines and Concurrency — Junior Level in your own words and name the problem it solves.
2. How would you apply the ideas around Introduction, Prerequisites, Glossary in a realistic engineering change?
3. What failure mode or misuse should you look for, and what evidence would reveal it?
4. What small example would prove that you can apply Goroutines and Concurrency — Junior Level correctly?
5. What observable result would convince you that the approach improved the system?
