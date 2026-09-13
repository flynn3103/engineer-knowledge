# Legacy Code — Professional

Martin Fowler’s strangler pattern replaces capability by routing; Kubernetes API migrations use served/storage versions and conversion; large databases use expand-contract schemas so mixed application versions remain compatible. These mechanisms make modernization a controlled operational process.

At 10× estate size, scarce expertise and test environments dominate. At 100×, dependency maps, regulatory constraints, and migration coordination become portfolio risks. Track hotspot risk, unsupported runtime exposure, incident share, change lead time, migration age, and old-path traffic.

## Design and operations checklist

1. Tie modernization to an outcome and risk.
2. Discover dependencies and undocumented contracts.
3. Establish characterization and production baselines.
4. Introduce routing or abstraction seams.
5. Migrate reversible slices with comparison telemetry.
6. Fund old-path removal and knowledge transfer.

```text
BASELINE -> SEAM -> PARALLEL PATH -> COMPARE -> SHIFT -> REMOVE
           preserve behavior + rollback + accountable ownership
```

## Test yourself

1. Build a portfolio model for ten legacy systems competing for investment.
2. How do you test a migration with undocumented consumers?
3. Which metric proves the new path is operationally better?
4. When should a rewrite be rejected?

## Further reading

- Michael Feathers, *Working Effectively with Legacy Code*.
- Martin Fowler, *Refactoring* and Strangler Fig Application.
- Kent Beck, *Tidy First?*.
