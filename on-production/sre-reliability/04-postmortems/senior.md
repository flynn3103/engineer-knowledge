# Postmortems — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Can you use incident learning to change system architecture and reliability investment under uncertainty?

---

## Look for recurring mechanisms

Aggregate postmortems by failure mechanism: overload, unsafe rollout, dependency timeout, ambiguous ownership, or missing recovery path. A recurring pattern merits an architectural control, not another local reminder. Preserve information hiding: teams should publish failure contracts and budgets, not expose every internal implementation detail.

## Scenario

Three incidents involve cascading retries across services. Individual actions add alarms, but the system-wide fix is a bounded retry contract, shared deadline propagation, and load tests that model dependency degradation. Each service retains its own implementation while honoring a common client contract.

## Choose investments

Compare prevention, faster detection, containment, and recovery against likelihood and impact. A rare catastrophic data-loss path can outweigh frequent minor alert noise. State uncertainty and use experiments—chaos tests, restore drills, or canaries—to obtain evidence.

## Apply it

1. Cluster three hypothetical incidents by mechanism.
2. Propose one system control and its adoption boundary.
3. Define evidence that the control reduces recurrence.

## Verify your work

- The proposed control addresses multiple incidents, not only wording.
- Teams can adopt the contract without sharing internals.
- Success is measured by a failure-path outcome.

## Review questions

- When does a recurring incident justify architectural investment?
- Why are reminders weak controls?
- How can a shared contract preserve team autonomy?
