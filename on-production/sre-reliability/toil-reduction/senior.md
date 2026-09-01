# Toil Reduction — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Can you choose automation architecture that lowers operational load without creating opaque, high-blast-radius control systems?

---

## Establish automation invariants

Automation needs an authority boundary, audit trail, rate limits, safe defaults, and human override. Keep policy decisions separate from executors so rules can evolve and actions can be simulated. The invariant is not “automation always succeeds”; it is “failed automation is bounded and diagnosable.”

## Scenario

A fleet remediation service restarts unhealthy workers. At scale, a bad health signal could restart every worker. Contain it with regional quotas, staged rollout, a control-plane kill switch, and a requirement that the service preserve a minimum healthy fraction. A manual approval gate remains for cross-region action.

## Trade-offs

Central automation standardizes safety but can become a bottleneck. Team-owned scripts preserve context but duplicate risky patterns. Offer a shared execution platform with local, reviewed policy modules and telemetry.

## Apply it

1. Define safety invariants for a remediation system.
2. Design staged scope from one instance to one region.
3. Identify a policy decision that must remain reviewable.

## Verify your work

- A faulty input cannot exceed the defined blast-radius quota.
- Every action is attributable and reversible where possible.
- Simulations test kill-switch and partial-failure behavior.

## Review questions

- What makes automation failure bounded?
- Why separate a policy engine from an executor?
- When is centralized automation a bottleneck?
