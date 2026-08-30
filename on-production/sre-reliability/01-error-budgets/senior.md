# Error Budgets — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Can you design error-budget policy for an evolving, multi-region journey while exposing its assumptions and failure modes?

---

## Architecture and invariants

Treat the budget as a contract around a user outcome. Its invariants are a stable eligibility definition, reproducible data, and a policy that changes behavior before repeated harm. Keep the SLI query versioned with the service; changing labels, retries, or regional routing can otherwise rewrite history.

## Regional scenario

An active-active checkout journey has 99.95% monthly availability. One region loses a payment route. A global aggregate can hide a regional disaster if most traffic remains healthy. Maintain both journey-level global SLOs and regional diagnostic objectives. Fail traffic over only after verifying the target region has capacity and idempotency protects repeated attempts.

| Choice | Favors | Cost |
|---|---|---|
| One global budget | Simple customer promise | Masks localized harm |
| Per-region budget | Detects inequity and routing faults | More policy complexity |
| Component budgets | Faster diagnosis | Can distract from outcome |

## Evidence before policy

Backtest candidate burn alerts against incidents and known traffic peaks. Sample eligible requests against traces. Review how a release freeze would have affected delivery and whether the error source was controllable. A policy based only on a preferred percentage is not an engineering decision.

## Apply it

1. List three assumptions behind a current SLI query.
2. Design global and regional measures for one journey.
3. Run a tabletop failure-over and identify budget-accounting effects.

## Verify your work

- Historical query results are reproducible after a dashboard change.
- A regional outage is visible even when global availability remains high.
- Policy actions map to evidence and a named decision owner.

## Review questions

- Which assumptions can make a budget calculation invalid?
- Why can a global SLO hide regional harm?
- What evidence should justify a release-freeze policy?
