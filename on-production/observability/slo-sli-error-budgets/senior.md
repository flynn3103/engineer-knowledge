# SLO, SLI, and Error Budgets — Senior

<!-- level-focus -->
At senior level, define system-level objectives that expose dependencies and prevent local optimization.

## Model the promise end to end

Checkout success depends on gateway, inventory, payment, and notification boundaries. Measure the user outcome at the edge, then use component objectives to diagnose contribution; do not claim the customer promise is met because each internal service meets its own number. State ownership and the behavior during a dependency outage, including graceful degradation.

Use error-budget consumption as evidence for architecture work: recurring payment timeouts may justify isolation, caching, or provider failover. Verify proposals with dependency failure drills and before/after burn-rate evidence.

## Apply it

1. Define the end-to-end SLI and dependency indicators.
2. Identify one shared failure that local dashboards would hide.
3. Test the degradation path and record budget impact.

## Verify your work

- The edge SLI matches what a user experiences.
- Dependency failures produce distinguishable evidence.

## Review questions

- Why do component SLOs not automatically compose into a user SLO?
- What decision should a budget policy make reversible?
