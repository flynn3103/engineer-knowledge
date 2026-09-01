# Load Shedding — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Can you architect overload protection across services while preserving fairness, recovery, and critical business invariants?

---

## Protect the dependency graph

Load shedding must follow bottlenecks, not organizational boundaries. Model where requests fan out, share pools, or retry. Preserve invariants such as authenticated emergency access and no duplicate writes. A service that sheds locally while its clients retry across five replicas may increase total pressure.

## Scenario

Marketing traffic overwhelms catalog and begins starving order inventory checks. Gateway quotas protect interactive purchase traffic; catalog returns cached pages; background indexing pauses; service deadlines prevent late work reaching inventory. Recovery gradually increases admission to avoid a retry surge.

## Fairness trade-offs

Per-tenant quotas protect small customers from a noisy neighbor but require trusted identity. Global probabilistic shedding is simple but may harm premium or safety-critical paths. Explicitly document who receives reserved capacity and why; fairness is a product decision with technical enforcement.

## Apply it

1. Map a request's shared bottlenecks and retry paths.
2. State two protected invariants and one fairness rule.
3. Plan a controlled recovery ramp after overload.

## Verify your work

- Load tests show no amplification through retries.
- Reserved traffic receives measurable protection.
- Recovery does not immediately recreate saturation.

## Review questions

- Why must shedding follow the dependency graph?
- What makes a quota fair or unfair?
- Why is recovery ramping necessary?
