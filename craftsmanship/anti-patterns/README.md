# Anti-Patterns

## Purpose

Anti-patterns are tempting solutions that repeatedly create avoidable cost. Use these guides to recognize the shape, choose a safer next step, and prevent the same problem from returning.

## Sections

- [Development](01-development/README.md): code structure, shortcuts, and over-engineering.
- [Design](02-design/README.md): object misuse, coupling, state, and abstraction failures.
- [Concurrency](03-concurrency/README.md): synchronization, coordination, and shared-state mistakes.
- [Async](04-async/README.md): error handling, execution shape, and lifecycle misuse.
- [Testing](05-testing/README.md): tests that are fragile, flaky, unclear, slow, or over-mocked.
- [Performance](06-performance/README.md): unmeasured optimization, repeated work, allocation, and data-structure mistakes.
- [At Scale](07-at-scale/README.md): architecture guardrails, debt control, hotspots, and safe large-system change.

## How to use the guides

1. Start with the section closest to the problem you can observe.
2. Read the guide for your current level.
3. Make one scoped change and verify it with a test, measurement, or reviewable check.
4. Move up a level when the same decision affects a wider boundary.
