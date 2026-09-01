# Async

## Purpose

This section covers async anti-patterns: recurring choices that make software harder to change, operate, or trust.

## Topics

- [Async Error-Handling Anti-Patterns](01-error-handling/junior.md): lost exceptions, unobserved failures, and error paths with no owner.
- [Async Execution-Shape Anti-Patterns](02-execution-shape/junior.md): accidental serial work, unbounded fan-out, and blocking work inside async paths.
- [Async Misuse Anti-Patterns](03-misuse/junior.md): using asynchronous APIs without lifecycle, cancellation, or backpressure discipline.

## Learning path

- **Junior:** recognize the smell and improve a small change safely.
- **Middle:** diagnose the pattern in a component and explain the trade-off.
- **Senior:** manage the pattern across a system boundary.
- **Professional:** establish a measurable prevention practice across teams.
