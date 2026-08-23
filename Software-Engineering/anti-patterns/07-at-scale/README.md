# Anti-Patterns at Scale

> Managing anti-patterns across an entire codebase and over time — the staff/principal-level view of enforcing, prioritizing, and removing bad shapes at scale rather than fixing one file at a time.

## Topics

| # | Topic | What you'll learn |
|---|-------|-------------------|
| 01 | [Architecture Fitness Functions](01-architecture-fitness-functions/junior.md) | Making a bad shape fail the build — ArchUnit, import-linter, dependency-cruiser, madge |
| 02 | [Anti-Pattern Budgets & Ratcheting](02-anti-pattern-budgets-and-ratcheting/junior.md) | Stopping a problem from getting worse while cleaning up — betterer, ESLint `--max-warnings`, SonarQube new-code gates |
| 03 | [Hotspot Analysis](03-hotspot-analysis/junior.md) | Finding which of a thousand smells actually hurts — git-log mining, code-maat, churn × complexity |
| 04 | [Automated Large-Scale Refactoring](04-automated-large-scale-refactoring/junior.md) | Fixing the same thing safely across hundreds of files — OpenRewrite, jscodeshift, Comby, Semgrep |
| 05 | [Strangler Fig & Seams](05-strangler-fig-and-seams/junior.md) | Replacing a bad shape without a rewrite or a flag day — branch by abstraction, seams, characterization tests |
| 06 | [Expand-Contract Refactors](06-expand-contract-refactors/junior.md) | Changing a contract nothing can change atomically — parallel change, deprecation, dual-write/dual-read |
| 07 | [Premature Abstraction at Scale](07-premature-abstraction-at-scale/junior.md) | When the "clean" abstraction is itself the anti-pattern — rule of three, AHA, inlining the wrong abstraction |

## How to use this section

Each topic has five depth levels — **junior → middle → senior → professional** — plus an **interview** Q&A bank and hands-on **tasks**. Each topic folder also includes `find-bug.md` (spot a flawed application of the technique) and `optimize.md` (make a slow/unsafe implementation fast and safe). Start at your level and climb.

---

> Part of the [Anti-Patterns](../README.md) roadmap.
