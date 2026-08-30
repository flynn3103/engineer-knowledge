# Error Budgets — Professional

<!-- level-focus -->
At professional level, focus on this question:

> Can you operate an organization-wide error-budget program that makes reliability investment and delivery trade-offs observable and reversible?

---

## Operating model

Product teams own journey objectives; a reliability enablement group supplies standards, tooling, and independent challenge. Publish a small SLO catalog with owner, query version, policy, and review date. Avoid a central committee approving every change: require review only for defined burn states or high-risk exceptions.

## Delivery scenario

Several teams migrate checkout to a new payments stack. Decompose work into canary, regional expansion, and full cutover, each with an expected budget cost and rollback condition. The program exit condition is not deployment completion: it is two billing cycles with stable journey SLO, reconciled payments, and accepted ownership.

## Governance and evidence

Review SLO coverage, chronic budget burn, exception use, and customer-impact distribution. Guard against gaming: changing denominators after an incident, excluding inconvenient traffic, or setting targets without product agreement. Escalate unresolved risk to the accountable product leader with facts and options.

## Apply it

1. Define a catalog entry and quarterly review process.
2. Plan a phased migration with budget gates and rollback conditions.
3. Choose two program metrics that cannot be improved merely by changing labels.

## Verify your work

- Teams can make normal release decisions without central delay.
- Exceptions have expiry, accountable approver, and follow-up evidence.
- Program reports show user outcomes alongside delivery throughput.

## Review questions

- How can an error-budget program be gamed?
- What makes a migration increment reversible?
- Which decisions belong to teams versus central enablement?
