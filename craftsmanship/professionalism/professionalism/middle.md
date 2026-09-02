# Engineering Professionalism — Middle

At middle level, professionalism moves from personal reliability to team coordination:

> How do I make useful commitments when scope, dependencies, and estimates are uncertain?

Prerequisite: [`junior.md`](junior.md).

## Saying no without blocking the goal

A professional “no” protects an outcome or constraint. Use this structure:

1. acknowledge the underlying need;
2. state the constraint and evidence;
3. explain the consequence of proceeding unchanged;
4. offer safer options;
5. identify who owns the trade-off.

Example:

> “We should not enable this migration for all tenants tonight. The rollback path has not been tested and the largest tenant exceeds our trial data size by 40×. We can run a 5% canary tonight, test restoration tomorrow, or accept the documented data-recovery risk with product and operations approval.”

This is not refusal for comfort. It keeps the business need visible while making risk explicit.

## Saying yes as a real commitment

Commit to an outcome with assumptions, scope, and checkpoints—not to hope. When evidence changes, renegotiate immediately. Do not keep an obsolete promise by hiding defects or working unsustainable hours.

## Estimation as forecasting

Break work into discovery, implementation, validation, rollout, and operational readiness. Use ranges and confidence:

| Forecast | Meaning |
|---|---|
| 50% date | Reasonable outcome if assumptions hold |
| 85% date | Includes likely integration and review variability |
| Tail risk | Named event that can exceed the range |

Track estimates and outcomes. Learn whether errors come from unknown scope, dependencies, interruptions, or execution.

## Acceptance before implementation

Write examples jointly with product, QA, and operations:

```gherkin
Given a customer has already paid an invoice
When the same payment request is retried
Then no second charge is created
And the original result is returned
```

Acceptance tests align stakeholders; unit tests protect implementation detail. Neither replaces exploratory, security, performance, or recovery testing.

## Collaboration and disagreement

Critique the proposal, not the person. State facts, assumptions, and values separately. Summarize the strongest opposing view before responding. Once a decision is made, commit to execution unless new evidence changes the risk.

## Mentoring in daily work

Do not only provide answers. Ask the learner to predict, attempt, and explain. Pair on real work, give specific feedback, and gradually reduce support. The goal is independent judgment, not dependence on the mentor.

## Test yourself

1. Write a professional “no” to an unsafe production change.
2. Why should estimates include validation and rollout?
3. What does an acceptance test prove that a unit test may not?
4. How do you disagree and still support the final team decision?

Continue to [`senior.md`](senior.md).
