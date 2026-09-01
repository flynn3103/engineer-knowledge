# Dependency-Breaking Techniques — Professional

At organization scale, dependency breaking enables independent delivery. It needs explicit ownership, compatibility policy, and a rollout plan—not just cleaner local code.

## Make boundary work operable

Define the contract, owning team, error semantics, service objectives, versioning policy, and deprecation path. Provide reference fakes or contract tests so consumers do not recreate assumptions independently.

## Roll out in stages

1. Baseline existing behavior and operational metrics.
2. Introduce a stable facade with compatibility defaults.
3. Migrate a small consumer cohort first.
4. Compare correctness, latency, and failures between paths.
5. Expand gradually; keep rollback cheap.
6. Remove the legacy path and its ownership burden.

## Avoid common traps

- A shared “common” abstraction that becomes every team’s bottleneck.
- Dual writes without reconciliation or a clear authority.
- Permanent feature flags with no retirement owner.
- Tests that fake a contract no real provider promises.

The outcome is a boundary that lets teams change their internals independently while preserving an observable, managed contract.
