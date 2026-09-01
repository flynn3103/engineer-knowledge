# Error Budgets — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Can you implement a service error-budget policy that guides releases without confusing dependency noise for user harm?

---

## Build the measurement boundary

Use an SLI at the request boundary users experience. For checkout, count completed purchase attempts, not pod health or a database's internal error rate. Define exclusions as code-reviewed rules: malformed requests may be excluded; requests rejected because your rate limiter is full are normally not.

## Choose a policy

| Burn state | Signal | Release response |
|---|---|---|
| Healthy | Budget remains within planned range | Normal rollout |
| Fast burn | Short window consumes budget rapidly | Pause broad rollout; investigate |
| Exhausted | Window budget is gone | Freeze risky changes; prioritize reliability |

Use both a short and long window. A five-minute spike alone can page unnecessarily; a 30-day average alone detects danger too late. Alert on a rate of budget consumption, then connect the alert to an explicit release decision.

## Integration scenario

The web service has 99.9% success while a payment-provider timeout begins. A retry change raises local HTTP success but duplicates some attempts. Do not claim the budget recovered until the user-facing completion SLI and duplicate-protection metric both agree. Add idempotency keys and bound retries before expanding traffic.

## Incremental adoption

Start with one journey, a documented query, and a weekly review. Compare dashboard totals with logs and synthetic transactions. Then automate a deployment gate that requires human acknowledgement on fast burn; avoid a fully automatic freeze before the data and ownership are trusted.

## Apply it

1. Write an eligible-request contract for one API.
2. Define one short-window and one long-window burn signal.
3. Draft the release action for each burn state.
4. Test a synthetic dependency timeout and compare SLI, retries, and duplicate outcomes.

## Verify your work

- Query results reconcile with a sampled request log.
- The release policy is understandable without dashboard access.
- A dependency failure cannot appear healthy only because retries hide it.

## Review questions

- Why are short and long budget windows used together?
- Which layer should define a user-facing SLI?
- How can retries make a local metric misleading?
