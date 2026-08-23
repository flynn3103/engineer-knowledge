# Concurrency Anti-Patterns

> Multi-thread, multi-goroutine, multi-process mistakes — coordinating mutable state across parallel execution, where symptoms are almost always intermittent.

## Topics

| # | Topic | What you'll learn |
|---|-------|-------------------|
| 01 | [Synchronization Misuse](01-synchronization/junior.md) | Double-Checked Locking, Volatile Misuse / Wrong Memory Ordering, Race-Prone Lazy Init |
| 02 | [Coordination](02-coordination/junior.md) | Lock Ordering Inconsistency (deadlock), Holding a Lock During I/O, Wrong Lock Granularity |
| 03 | [Shared State](03-shared-state/junior.md) | Shared Mutable State Without Protection, Busy Waiting / Spin Loop, Thread-Per-Request Without Bounds |

## How to use this section

Each topic has five depth levels — **junior → middle → senior → professional** — plus an **interview** Q&A bank and hands-on **tasks**. Each topic folder also includes `find-bug.md` (spot-the-race drills) and `optimize.md` (implementations to make safe and fast). Start at your level and climb.

---

> Part of the [Anti-Patterns](../README.md) roadmap.
