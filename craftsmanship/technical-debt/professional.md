# Technical Debt — Professional

Ward Cunningham’s metaphor distinguishes borrowing speed now from paying future interest. Google’s code-health and large-scale-change tooling lower repayment transaction cost. Kubernetes deprecation policy turns ecosystem compatibility debt into an explicit multi-release process.

At portfolio scale, unsupported platforms, fragmented ownership, and shared bottlenecks dominate local code smells. Track change lead time in hotspots, incident contribution, unsupported-version exposure, migration age, dependency risk, and capacity consumed by toil.

## Design and operations checklist

1. Connect debt to strategic outcomes and risks.
2. Estimate principal, recurring interest, and uncertainty.
3. Identify affected owners and dependencies.
4. Choose pay, contain, accept, or avoid explicitly.
5. Fund incremental migration and old-path removal.
6. Measure whether change cost and risk actually fall.

```text
CHOICE -> SHORT-TERM BENEFIT + PRINCIPAL + RECURRING INTEREST
         observe -> prioritize -> contain/pay -> verify -> prevent
```

## Test yourself

1. Build a debt portfolio model across twenty services.
2. Which debt deserves funding despite low current incident count?
3. How do you prevent a migration from creating permanent dual-system debt?
4. Which metric reveals repayment reduced business lead time?

## Further reading

- Ward Cunningham, “The WyCash Portfolio Management System.”
- Martin Fowler, Technical Debt Quadrant.
- Adam Tornhill, *Software Design X-Rays*.
- Google Engineering Practices and large-scale change literature.
