# Testing — Professional

Pact implements consumer-driven contracts; Hypothesis and QuickCheck generate property cases and shrink failures; PIT and Stryker perform mutation analysis; Testcontainers provides disposable real dependencies. Each solves a different evidence gap.

## Design and operations checklist

1. Map tests to failure modes and ownership.
2. Keep fast feedback near code and realistic evidence at boundaries.
3. Quarantine and fix flaky tests with an explicit SLO.
4. Version contracts and test data safely.
5. Test rollback, recovery, and production controls.
6. Measure escaped defects and feedback time, not test count.

```text
RISK -> CHEAPEST FAITHFUL TEST -> EVIDENCE -> RELEASE GUARD -> OUTCOME
```

## Test yourself

1. Design test architecture for 200 independently deployed services.
2. How do contract tests fail during semantic change?
3. Which tests should block release versus inform it?
4. How do you measure suite value?

## Further reading

- Meszaros, *xUnit Test Patterns*.
- Freeman and Pryce, *Growing Object-Oriented Software, Guided by Tests*.
- Humble and Farley, *Continuous Delivery*.
