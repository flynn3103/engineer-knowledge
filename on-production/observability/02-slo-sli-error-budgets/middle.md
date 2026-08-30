# SLO, SLI, and Error Budgets — Middle

<!-- level-focus -->
At middle level, choose SLO boundaries that guide local engineering decisions without creating misleading targets.

## Compose indicators

Give the API an availability SLO and a latency SLO; give an asynchronous worker freshness or completion SLO. Do not average a healthy low-volume route with a broken high-value route. Segment only on stable dimensions such as region or tier, and document why each segment matters.

When the budget burns quickly, pause risky releases, investigate the top failure mode, and use a smaller change or rollback. When it is healthy, the budget permits experimentation; it is not a score for punishing teams.

## Apply it

1. Map the checkout path and select two user-visible indicators.
2. Compare rolling and calendar windows for release feedback.
3. Write a burn-rate alert that needs both short and long windows.

## Verify your work

- Each SLO maps to an owner and a release decision.
- The alert catches sustained loss without paging for brief noise.

## Review questions

- When should two endpoints have separate objectives?
- Why can a short window alone create noisy pages?
