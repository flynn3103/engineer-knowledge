# Legacy Code — Senior

Modernize through vertical outcomes. Use strangler routing, branch by abstraction, expand-contract schemas, shadow reads, traffic comparison, and rollback. State invariants across old and new paths.

Prioritize hotspots by change frequency, incident impact, knowledge concentration, and strategic constraint. A stable old component with low change may deserve monitoring, not replacement.

Temporary dual paths need owners, telemetry, divergence handling, and removal dates. Rewrites fail when they postpone user value and rediscover undocumented behavior too late.

## Test yourself

1. Which invariant must both old and new paths preserve?
2. When is leaving legacy code alone correct?
3. How do shadow reads reveal semantic differences?
4. What exit criterion removes the old path?

Continue to [`professional.md`](professional.md).
