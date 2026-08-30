# Graceful Degradation — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Can you design degradation modes for a distributed product that remain truthful, recoverable, and compatible as dependencies evolve?

---

## Model modes explicitly

Define normal, degraded, and unavailable modes at product boundaries. Each mode specifies data source, freshness, user message, write behavior, and recovery rule. Keep compatibility in API contracts so older clients understand unavailable or stale responses rather than misreading them as success.

## Scenario

During a regional analytics outage, account pages serve cached profile information while writes queue only if idempotency and ordering are guaranteed. Billing and authorization remain fail-closed. On recovery, replay is rate-limited and reconciled; “eventually processed” is not enough without a way to detect failed replay.

## Trade-offs

More fallback paths improve availability but increase states to test and maintain. Favor a few product-meaningful modes over ad hoc exception handling. Use failure injection and customer-impact measures to prove a mode helps.

## Apply it

1. Specify mode contracts for one journey.
2. Identify one operation that must fail closed.
3. Design recovery and reconciliation evidence for queued work.

## Verify your work

- Clients render each mode correctly across supported versions.
- Fallback behavior is covered by dependency-failure tests.
- Recovery accounts for every accepted deferred operation.

## Review questions

- What fields make a degradation mode explicit?
- Why can more fallbacks reduce reliability?
- Which operations should fail closed?
