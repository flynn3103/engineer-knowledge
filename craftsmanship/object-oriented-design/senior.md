# Object-Oriented Design — Senior

Use domain events, aggregates, value objects, policies, and services only where they preserve real domain distinctions. Aggregate boundaries protect invariants and transaction scope; they should not mirror database tables or UI screens.

Design thread-safe objects with ownership, immutability, confinement, locks, or actors. Document atomic operations and never expose partially valid state.

Extension through polymorphism is valuable when variations share a stable contract. If consumers need type checks or subclasses reject base behavior, the hierarchy is lying. Favor replaceable collaborations and explicit data transformations when object identity adds no value.

## Test yourself

1. Which invariant defines an aggregate boundary?
2. How do you prevent partially valid concurrent state?
3. What signals a false inheritance hierarchy?
4. When is functional data transformation simpler than objects?

Continue to [`professional.md`](professional.md).
