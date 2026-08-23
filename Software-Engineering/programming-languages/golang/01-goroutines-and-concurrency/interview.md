# Goroutines and Concurrency — Interview Prep

> **Topic:** [Goroutines and Concurrency](../README.md)

---

## Conceptual / Foundational

**Q: What is a goroutine, and how is it different from an OS thread?**
A: A goroutine is a function scheduled by the Go runtime, not the OS, onto a small pool of OS threads. It starts with a ~2 KB stack that grows as needed, versus 1–8 MB for an OS thread, so spawning hundreds of thousands is practical.

**Q: What happens when `main()` returns while other goroutines are still running?**
A: The program exits immediately. The runtime does not wait for other goroutines to finish.

**Q: Difference between an unbuffered and a buffered channel?**
A: An unbuffered channel (`make(chan T)`) blocks the sender until a receiver is ready — it's a synchronization point. A buffered channel (`make(chan T, n)`) lets up to `n` sends complete without a receiver, only blocking once full.

**Q: What does closing a channel do?**
A: Signals no more values will be sent. Further sends panic. Receives on a closed channel return immediately with the zero value; the two-value form `v, ok := <-ch` reports `ok == false` once drained.

## Tricky / Trap Questions

**Q: What's wrong with this?**
```go
for i := 0; i < 3; i++ {
    go func() { fmt.Println(i) }()
}
```
A: Pre-Go 1.22, all goroutines share the same `i` — by the time they run it's likely `3` for all of them. Pass `i` as a parameter to fix on any version. (Go 1.22+ gives each iteration a fresh `i`, but relying on version-specific behavior in an interview answer is a weaker answer than knowing the parameter fix.)

**Q: A `WaitGroup`'s `Wait()` returns before all goroutines finished. Why?**
A: Almost always because `Add()` was called inside the goroutine instead of before `go` in the parent — `Wait()` can race ahead of a not-yet-executed `Add()`.

**Q: Why does sending on a channel that nobody ever reads leak memory?**
A: The sending goroutine blocks forever on the send, holding its stack and anything it captured (closures, connections) for the life of the program.

**Q: Is `sync.Mutex` safe to copy?**
A: No — copying a `Mutex` (directly or via a struct containing one) creates two independent locks guarding what was meant to be one critical section. `go vet` flags this.

## System / Design Scenarios

**Q: Design a function that fetches from 10 URLs concurrently and returns as soon as the first response arrives, canceling the rest.**
A: Spawn a goroutine per URL, each writing into a shared buffered channel (capacity 10, so no goroutine leaks waiting to send) wrapped by a `context.WithCancel`; on the first successful receive, call `cancel()` so in-flight HTTP requests using that context are aborted, then return.

**Q: How would you bound an ETL job so it never has more than 20 concurrent database writes, regardless of input size?**
A: A worker pool of 20 goroutines pulling from a job channel, or `errgroup.SetLimit(20)` if error propagation is also needed.

**Q: A service's goroutine count grows without bound over days. How do you find the leak?**
A: Pull `/debug/pprof/goroutine?debug=2` from the live process, group stacks by frequency, and look at the dominant repeated stack — it points at the exact blocking call that never returns.

## Behavioral / Experience

**Q: Tell me about a concurrency bug you shipped and how you found it.**
A: (Tailor to your experience — strong answers name the specific tool used to find it: `-race`, `pprof`, `goleak`, or a production graph, and describe the structural fix, not just the patch.)

---

## Cheat Sheet

```
Goroutine leak    → no reachable exit path (missing close/cancel/timeout)
Deadlock          → cyclic wait, "all goroutines are asleep" panic
Data race         → unsynchronized shared write, caught by -race
WaitGroup misuse  → Add() must happen before go, in the parent
Channel direction → sender closes, never the receiver
```

---

## Related Topics

- [Junior](junior.md) · [Middle](middle.md) · [Senior](senior.md) · [Professional](professional.md) · [Tasks](tasks.md)
