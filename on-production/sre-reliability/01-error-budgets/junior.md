# Error Budgets — Junior

<!-- level-focus -->
At junior level, focus on this question:

> Can you calculate a monthly availability error budget and use it to decide whether a proposed risky change should wait?

---

## The idea

An **SLO** is a target for a user-visible service measure, such as 99.9% successful checkout requests in 30 days. The **error budget** is the amount of failure that target permits. It is not permission to be careless; it is a concrete reliability limit that lets a team balance change against safety.

For a 30-day window, 99.9% availability permits 0.1% failure:

| SLO | Allowed failure | Approximate time in 30 days |
|---|---:|---:|
| 99.9% | 0.1% | 43 minutes |
| 99.95% | 0.05% | 22 minutes |
| 99.99% | 0.01% | 4 minutes |

The calculation is `window minutes × (1 - SLO)`. Use requests, not elapsed downtime, when different users are affected differently: `bad eligible requests / eligible requests` is the error rate.

## A small example

The checkout service handled 2,000,000 eligible requests this month. Its 99.9% success SLO permits 2,000 bad requests. The dashboard shows 1,500 failures, leaving 500 requests of budget. A schema migration expected to cause 900 failed requests should not run as planned; reduce its blast radius or defer it.

## Method

1. Find the service's published SLO and measurement window.
2. Confirm which requests are eligible; health probes and client mistakes often are not.
3. Calculate allowed failures and subtract observed failures.
4. State the result in a change review: remaining budget, expected cost, and mitigation.
5. Escalate when the budget is exhausted instead of silently accepting another risk.

## Common mistakes

- Treating a 99.9% target as a promise of zero incidents.
- Counting every HTTP 4xx as server failure when the SLI definition excludes invalid user input.
- Using a dashboard percentage without checking its window and denominator.
- Spending budget on a change without estimating its failure exposure.

## Apply it

1. Choose one user journey and invent a 28-day, 99.9% SLO.
2. Calculate its allowed bad requests for 500,000 eligible requests.
3. Record three failure categories that should count and one that should not.
4. Evaluate a release expected to fail 40 requests against a remaining budget of 25.

## Verify your work

- Your allowed-failure calculation uses the stated window and denominator.
- Another engineer can reproduce the remaining-budget number from your inputs.
- Your release decision names a mitigation or a reason to defer.

## Review questions

- What is the relationship between an SLO and an error budget?
- Why must the eligible-request definition be explicit?
- What should happen when a planned change exceeds the remaining budget?
