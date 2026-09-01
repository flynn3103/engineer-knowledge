# Graceful Degradation — Professional

<!-- level-focus -->
At professional level, focus on this question:

> Can you establish product-wide degradation strategy that aligns teams, compliance, customer communication, and continuous recovery learning?

---

## Product resilience portfolio

Catalog critical journeys, allowed degraded modes, forbidden fallbacks, ownership, customer messages, and recovery evidence. Align these with legal and financial commitments: privacy controls and authorization may fail closed even when availability goals encourage a fallback. Keep contracts versioned across mobile, web, and partner APIs.

## Sustained scenario

A regional dependency outage lasts days. Teams progressively enable cached reads, delayed notifications, and explicit unavailable states, while preserving billing correctness and data residency. Customer support receives mode-specific guidance; recovery is staged, reconciles queued work, and verifies no data was silently lost. Each increment is reversible through flags with monitored effects.

## Governance and outcomes

Review fallback usage, stale-data age, deferred-work reconciliation, support contacts, and mode-test coverage. Retire unsafe or unused paths; every fallback is operational software with ownership and maintenance cost.

## Apply it

1. Build a degradation catalog for three journeys.
2. Define one legal or correctness constraint that forces fail-closed behavior.
3. Plan a mode exercise including customer communication and reconciliation.

## Verify your work

- Every published degradation mode has an owner, test, and recovery rule.
- Support and partner teams receive accurate mode information.
- Recovery evidence accounts for deferred and failed work.

## Review questions

- Why must degradation strategy include customer communication?
- Which constraints can override an availability fallback?
- How do you know a fallback path remains safe over time?
