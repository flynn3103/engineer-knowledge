# Testing

## Purpose

This section covers testing anti-patterns: recurring choices that make software harder to change, operate, or trust.

## Topics

- [Fragile Tests](01-fragile-tests/junior.md): tests coupled to incidental structure instead of observable behavior.
- [Flaky Tests](02-flaky-tests/junior.md): tests whose result changes with time, order, timing, or external state.
- [Mystery Guest](03-mystery-guest/junior.md): tests that rely on hidden files, databases, environment values, or shared setup.
- [Assertion Roulette](04-assertion-roulette/junior.md): many unlabeled assertions that make failures hard to diagnose.
- [Slow Tests](05-slow-tests/junior.md): tests that do unnecessary real I/O, broad setup, or serial work.
- [Over-Mocking](06-over-mocking/junior.md): tests that verify implementation choreography rather than behavior.

## Learning path

- **Junior:** recognize the smell and improve a small change safely.
- **Middle:** diagnose the pattern in a component and explain the trade-off.
- **Senior:** manage the pattern across a system boundary.
- **Professional:** establish a measurable prevention practice across teams.
