# Flaky Tests & Reliability

Treat flaky tests as defects: find the cause, restore trust, and prevent recurrence.

## Learn by level

- [Junior](junior.md) — recognize common sources of nondeterminism.
- [Middle](middle.md) — triage and remove timing, state, and dependency races.
- [Senior](senior.md) — design reliable suites and failure policies.
- [Professional](professional.md) — manage flake rate as an engineering health signal.

## Apply it

1. Reproduce the failure and record its conditions.
2. Classify the source: time, state, network, ordering, or product race.
3. Fix the cause instead of adding blind retries.
4. Quarantine unreliable tests from gating while an owner resolves them.
