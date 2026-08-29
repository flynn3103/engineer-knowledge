# Go

> Write a small correct program, shape it into maintainable packages, then operate it under real traffic.

Follow the roadmap in order if Go is new. If you already ship Go, start at the production problem you need to solve and use the earlier sections to close gaps.

## Roadmap

| Stage | Topic | Practice outcome |
|---|---|---|
| 1 | [Introduction to Go](01-introduction-to-go/README.md) | Install the toolchain, run a program, and use core Go commands. |
| 2 | [Goroutines and Concurrency](01-goroutines-and-concurrency/junior.md) | Coordinate work, cancellation, ownership, and shutdown. |
| 3 | [Go Runtime](02-go-runtime/junior.md) | Explain scheduler, allocation, stack, and garbage-collection evidence. |
| 4 | [Interfaces](03-interfaces/junior.md) | Put small contracts at consumer boundaries. |
| 5 | [Error Handling](04-error-handling/junior.md) | Preserve meaning, context, and retry decisions. |
| 6 | [HTTP and APIs](05-http-and-apis/junior.md) | Bound request lifetime and shut services down safely. |
| 7 | [Code Organization](06-code-organization/README.md) | Organize modules, packages, dependencies, and releases. |
| 8 | [Database and Distributed Systems](06-database-and-distributed-systems/junior.md) | Handle transactions, retries, queues, caching, and partial failure. |
| 9 | [Production Debugging](07-production-debugging/junior.md) | Use profiles, traces, logs, and metrics to test a diagnosis. |

## Use the roadmap on real work

1. Reproduce one behavior with `go test`, a focused program, or a controlled request.
2. Run `go test -race ./...` when shared state or concurrency is involved.
3. Capture a benchmark, profile, trace, or request timing before optimizing.
4. Make one reversible change.
5. Run the same evidence collection again and compare.

Avoid memorizing Go trivia without a program that makes the rule observable.

Part of the [Programming Languages](../README.md) roadmap.
