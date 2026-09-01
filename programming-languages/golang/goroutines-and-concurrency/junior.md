# Goroutines and Concurrency — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Goroutines and Concurrency** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
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

## Apply it

1. Choose one small, known input for **Goroutines and Concurrency**.
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

- What problem does Goroutines and Concurrency solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
