# Concurrency Patterns

> Reusable solutions to the recurring problems of coordinating work across threads, cores, and machines — the patterns the 1994 Gang of Four catalog never covered.

## Topics

| # | Topic | What you'll learn |
|---|-------|-------------------|
| 01 | [Active Object](01-active-object/junior.md) | Decoupling method invocation from execution — each object runs on its own thread, requests queued |
| 02 | [Monitor Object](02-monitor-object/junior.md) | Letting only one method run inside an object at a time, cooperating via condition variables |
| 03 | [Reactor](03-reactor/junior.md) | A single-threaded event loop demultiplexing I/O readiness and dispatching to handlers |
| 04 | [Proactor](04-proactor/junior.md) | Asynchronous, completion-based event handling where the OS performs the I/O |
| 05 | [Thread Pool](05-thread-pool/junior.md) | Reusing a bounded set of worker threads to execute a stream of tasks |
| 06 | [Producer–Consumer](06-producer-consumer/junior.md) | Decoupling producers from consumers through a shared bounded buffer |
| 07 | [Future / Promise](07-future-promise/junior.md) | A placeholder for a value that doesn't exist yet |
| 08 | [Half-Sync/Half-Async](08-half-sync-half-async/junior.md) | Separating simple synchronous processing from fast asynchronous I/O via a queueing layer |
| 09 | [Leader/Followers](09-leader-followers/junior.md) | A pool of threads taking turns being the one that waits for events |
| 10 | [Double-Checked Locking](10-double-checked-locking/junior.md) | Lazily initializing a shared resource while locking only on first access |
| 11 | [Balking](11-balking/junior.md) | Refusing a request immediately when an object is in the wrong state, instead of blocking |

## How to use this section

Each topic has five depth levels — **junior → middle → senior → professional** — plus an **interview** Q&A bank and hands-on **tasks**. Each topic folder also includes `find-bug.md` and `optimize.md` practice files. Start at your level and climb.

---

> Part of the [Design Patterns](../README.md) roadmap.
