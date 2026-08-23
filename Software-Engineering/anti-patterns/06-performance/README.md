# Performance Anti-Patterns

> Code-level performance anti-patterns — the wrong shapes that waste CPU, memory, or I/O inside a single function or loop, spotted by reading code, not drawing a system diagram.

## Topics

| # | Topic | What you'll learn |
|---|-------|-------------------|
| 01 | [Premature Optimization Traps](01-premature-optimization-traps/junior.md) | Code twisted for speed that was never measured and rarely matters; measuring first |
| 02 | [N+1 in Code](02-n-plus-one-in-code/junior.md) | Per-item work in a loop that should be done once; batching, hoisting, preloading |
| 03 | [Unnecessary Allocation](03-unnecessary-allocation/junior.md) | Throwaway objects, boxing, and copies churned in a hot path; reusing buffers, avoiding boxing |
| 04 | [Wrong Data Structure](04-wrong-data-structure/junior.md) | A collection whose cost model fights the access pattern; matching structure to operations |

## How to use this section

Each topic has five depth levels — **junior → middle → senior → professional** — plus an **interview** Q&A bank and hands-on **tasks**. Each topic folder also includes `find-bug.md` (spot-the-anti-pattern drills) and `optimize.md` (profile and fix a slow implementation with numbers to prove the win). Start at your level and climb.

---

> Part of the [Anti-Patterns](../README.md) roadmap.
