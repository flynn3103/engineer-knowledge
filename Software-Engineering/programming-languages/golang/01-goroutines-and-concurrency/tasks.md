# Goroutines and Concurrency — Hands-On Tasks

> **Topic:** [Goroutines and Concurrency](../README.md)

---

## Warm-Up

1. Write a program that spawns 5 goroutines, each printing its own index, and correctly waits for all of them using `sync.WaitGroup`.
2. Deliberately reproduce the captured-loop-variable bug, confirm the output, then fix it by passing the variable as a parameter.
3. Build an unbuffered channel handshake: goroutine A sends 10 numbers one at a time; goroutine B receives and prints each, doubled.

## Core

4. Implement a worker pool with a configurable number of workers that processes 1,000 jobs from a channel and collects results into a slice, safely.
5. Build a fan-out/fan-in pipeline: one generator goroutine, three "square" workers, one merger — verify all input values appear exactly once in the output (in any order).
6. Add a `context.WithTimeout` to a simulated slow operation and demonstrate that the caller returns promptly on timeout instead of waiting for the full operation.
7. Rewrite task 4 using `errgroup` instead of a manual channel + `WaitGroup`, and make one job intentionally fail — confirm the first error is returned and remaining work is canceled via the shared context.

## Advanced

8. Write a test that intentionally leaks a goroutine (blocks on an unbuffered channel with no receiver) and use `go.uber.org/goleak` to make the test fail because of it. Then fix the leak.
9. Build a semaphore-bounded dispatcher (buffered channel of `struct{}`) that limits concurrent execution to N, and load-test it with 10x N submitted jobs to confirm no more than N ever run simultaneously (instrument with an atomic counter).
10. Reproduce a deadlock on purpose (two goroutines each waiting to send on the other's unbuffered channel) and observe Go's "all goroutines are asleep" panic. Explain in writing what would need to differ for this to hang silently instead of panicking (hint: a third, unrelated goroutine still running).

## Capstone

11. Build a small concurrent URL fetcher: given a list of 50 URLs, fetch at most 10 concurrently, respect a 2-second per-request timeout, collect (URL, status code, error) for every one, and print a summary. Use `errgroup.SetLimit`, `context.WithTimeout` per request, and run the whole thing under `-race` and `goleak` in a test.

## If you can do all of these, you have the middle level

You can spawn, join, bound, and cancel concurrent work correctly, and you know how to prove — with `-race` and `goleak`, not just "it seemed fine" — that you didn't introduce a race or a leak.

---

## Related Topics

- [Junior](junior.md) · [Middle](middle.md) · [Senior](senior.md) · [Professional](professional.md) · [Interview](interview.md)
