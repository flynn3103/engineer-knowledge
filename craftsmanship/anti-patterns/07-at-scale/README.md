# At Scale

## Purpose

This section covers at scale anti-patterns: recurring choices that make software harder to change, operate, or trust.

## Topics

- [Architecture Fitness Functions](01-architecture-fitness-functions/junior.md): important architectural qualities that are discussed but never checked.
- [Anti-Pattern Budgets & Ratcheting](02-anti-pattern-budgets-and-ratcheting/junior.md): known debt that grows because no limit or improvement rule exists.
- [Hotspot Analysis](03-hotspot-analysis/junior.md): refactoring chosen by taste instead of change and complexity evidence.
- [Automated Large-Scale Refactoring](04-automated-large-scale-refactoring/junior.md): repetitive edits performed manually or automated edits shipped without safeguards.
- [Strangler Fig & Seams](05-strangler-fig-and-seams/junior.md): a legacy system is replaced in one risky move instead of gradually at a controlled boundary.
- [Expand-Contract Refactors](06-expand-contract-refactors/junior.md): a shared interface or data shape changes in a single breaking deployment.
- [Premature Abstraction at Scale](07-premature-abstraction-at-scale/junior.md): a shared platform or common layer is created before stable common needs exist.

## Learning path

- **Junior:** recognize the smell and improve a small change safely.
- **Middle:** diagnose the pattern in a component and explain the trade-off.
- **Senior:** manage the pattern across a system boundary.
- **Professional:** establish a measurable prevention practice across teams.
