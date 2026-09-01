# Concurrency

## Purpose

This section covers concurrency anti-patterns: recurring choices that make software harder to change, operate, or trust.

## Topics

- [Synchronization Misuse Anti-Patterns](01-synchronization/junior.md): unsafe locking, lock ordering, and synchronization that does not protect the real invariant.
- [Coordination Anti-Patterns](02-coordination/junior.md): workers that wait, signal, retry, or cancel without a clear protocol.
- [Shared State Anti-Patterns](03-shared-state/junior.md): mutable state shared by concurrent work without a single owner.

## Learning path

- **Junior:** recognize the smell and improve a small change safely.
- **Middle:** diagnose the pattern in a component and explain the trade-off.
- **Senior:** manage the pattern across a system boundary.
- **Professional:** establish a measurable prevention practice across teams.
