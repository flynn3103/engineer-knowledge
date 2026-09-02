# Engineering Professionalism — Senior

At senior level, professionalism means protecting system and team outcomes under competing pressure:

> How do I preserve safety, honesty, and sustainable delivery when the easiest local action transfers risk to others?

Prerequisite: [`middle.md`](middle.md).

## Make pressure visible

Deadlines, incidents, executive attention, and customer escalation narrow thinking. Establish decision roles, time boxes, rollback conditions, and communication cadence before urgency becomes chaos.

During an incident:

- separate mitigation from root-cause investigation;
- preserve evidence and a shared timeline;
- assign one incident commander and explicit workstreams;
- communicate facts, hypotheses, actions, and uncertainty separately;
- stop changes that increase blast radius without a clear prediction.

## Protect quality through risk-based scope

Quality is not a single gate. Identify non-negotiable controls by failure impact:

| Risk | Required evidence |
|---|---|
| Data loss or corruption | migration rehearsal, backup validation, restore test |
| Authorization failure | security review, negative tests, audit evidence |
| Availability regression | load test, canary, rollback, saturation metrics |
| Minor UI defect | focused acceptance test and reversible release |

When time is fixed, reduce scope or exposure. Do not describe omitted safety work as “technical debt” unless ownership, impact, and repayment are explicit.

## Lead difficult commitments

Translate strategy into outcomes, decision boundaries, dependencies, and evidence. Challenge plans that require permanent overtime or invisible coordination. Escalate when authority and accountability are separated—for example, when a team owns reliability but cannot control release volume.

## Ethical engineering decisions

Identify affected people, not only direct users. Ask about privacy, accessibility, security, bias, misuse, environmental cost, and power imbalance. Legal approval is a floor, not proof that a system is responsible.

Use documented risk review for consequential systems. Record dissent and require accountable owners for accepted risk.

## Build capability through mentoring

Map critical expertise and single-person dependencies. Use pairing, design reviews, rotations, incident shadowing, and teaching assignments. Evaluate mentoring by the learner’s expanding autonomy and judgment.

## Failure modes

- **Hero culture:** rewards rescue while hiding preventable system weakness.
- **False certainty:** turns estimates into promises and punishes updates.
- **Consensus theater:** suppresses disagreement without resolving it.
- **Process compliance:** checks boxes without protecting the underlying risk.
- **Mentor bottleneck:** one expert reviews everything and prevents growth.

## Test yourself

1. A deadline cannot move. How do you choose scope and safety controls?
2. When should an engineering risk be escalated beyond the team?
3. How would you document ethical dissent about a legal product feature?
4. Which signals reveal that mentoring creates dependence instead of autonomy?

Continue to [`professional.md`](professional.md).
