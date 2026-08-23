# Async Anti-Patterns

> Event-loop / Promise / async-await mistakes — the single-threaded cooperative-multitasking world of JavaScript, Python `asyncio`, C# `async/await`, and Rust `tokio`.

## Topics

| # | Topic | What you'll learn |
|---|-------|-------------------|
| 01 | [Error Handling](01-error-handling/junior.md) | Swallowed Promise Rejection, Floating Promise, Fire and Forget (without logging), Forgotten `await` |
| 02 | [Execution Shape](02-execution-shape/junior.md) | `await` in a Loop, Promise Chain Hell / Callback Pyramid, Mixing Callbacks and Promises |
| 03 | [Misuse](03-misuse/junior.md) | Promise Constructor Anti-Pattern, `async` Without `await` |

## How to use this section

Each topic has five depth levels — **junior → middle → senior → professional** — plus an **interview** Q&A bank and hands-on **tasks**. Each topic folder also includes `find-bug.md` (spot-the-async-bug drills) and `optimize.md` (implementations to make correct and parallel). Start at your level and climb.

---

> Part of the [Anti-Patterns](../README.md) roadmap.
