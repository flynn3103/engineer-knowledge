# Refactoring as a Discipline — Professional

## Goal

Make structural improvement routine work that supports delivery.

## Make the case

- Connect the change to faster delivery, lower incident risk, or cheaper onboarding.
- Break large work into reversible, deployable steps.
- Show the hotspot and the upcoming feature that needs it.

## Team workflow

- Review refactor-only changes for behavior preservation and scope.
- Keep feature and cleanup commits separate.
- Track lead time, failure rate, and hotspot churn; do not worship a single code metric.
- Use the Mikado approach: map dependencies, make one change, revert when green is lost, then retry in a safe order.
