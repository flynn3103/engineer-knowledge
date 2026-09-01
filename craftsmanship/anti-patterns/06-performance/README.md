# Performance

## Purpose

This section covers performance anti-patterns: recurring choices that make software harder to change, operate, or trust.

## Topics

- [Premature Optimization Traps](01-premature-optimization-traps/junior.md): complex optimizations added before a measured performance problem exists.
- [N+1 in Code](02-n-plus-one-in-code/junior.md): a loop triggers one expensive lookup or operation for each item.
- [Unnecessary Allocation](03-unnecessary-allocation/junior.md): temporary objects or copies created repeatedly on a hot path.
- [Wrong Data Structure](04-wrong-data-structure/junior.md): a collection does not match the operations performed most often.

## Learning path

- **Junior:** recognize the smell and improve a small change safely.
- **Middle:** diagnose the pattern in a component and explain the trade-off.
- **Senior:** manage the pattern across a system boundary.
- **Professional:** establish a measurable prevention practice across teams.
