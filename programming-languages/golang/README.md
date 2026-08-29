# Go

> The practical, production-facing slice of Go: the seven things that actually decide whether a Go service holds up once it leaves your laptop — concurrency, the runtime underneath it, interfaces, errors, HTTP, data, and how you debug all of it live.

This roadmap is intentionally narrow. It does not re-teach Go syntax — it assumes you can already write a working program — and it skips ecosystem trivia (which CLI framework, which ORM). Instead it goes deep on the handful of things that separate "it compiles" from "it survives production": how goroutines and channels actually behave under load, what the runtime is doing behind the scenes, how to design interfaces and errors that don't rot, how to build HTTP services and data layers that fail gracefully, and how to debug a live service without guessing.

## Topics

| # | Topic | What you'll learn |
|---|-------|-------------------|
| 01 | [Goroutines and Concurrency](01-goroutines-and-concurrency/junior.md) | Goroutines, channels, worker pools, fan-in, fan-out, context cancellation, race conditions, deadlocks, and when *not* to use channels |
| 02 | [Go Runtime](02-go-runtime/junior.md) | Scheduler, garbage collector, stack growth, escape analysis, memory allocation, and why simple Go code can still behave differently under load |
| 03 | [Interfaces](03-interfaces/junior.md) | Implicit interfaces, type assertions, the empty interface, interface design, mocks, dependency injection, and why small interfaces are usually better |
| 04 | [Error Handling](04-error-handling/junior.md) | `error`, wrapping, sentinel errors, custom errors, `errors.Is`, `errors.As`, and building error flows that are boring but debuggable |
| 05 | [HTTP and APIs](05-http-and-apis/junior.md) | Middleware, handlers, timeouts, retries, connection pooling, graceful shutdown, request context, and writing APIs that do not fall apart in production |
| 06 | [Database and Distributed Systems](06-database-and-distributed-systems/junior.md) | Transactions, connection pools, idempotency, queues, caching, rate limits, retries, locks, and handling partial failures properly |
| 07 | [Production Debugging](07-production-debugging/junior.md) | `pprof`, traces, logs, metrics, goroutine leaks, memory leaks, slow queries, high latency, and how to debug a live service without randomly guessing |

## How to use this section

Each topic has four depth levels—**junior → middle → senior → professional**—and every guide ends with unanswered comprehension questions. Start at your level and climb. The topics build on each other loosely: concurrency and the runtime (01–02) explain *why* Go behaves the way it does; interfaces and errors (03–04) are the design vocabulary you use everywhere; HTTP, data, and debugging (05–07) are where all of it gets exercised under real traffic.

---

> Part of the [Programming Languages](../README.md) roadmap.
