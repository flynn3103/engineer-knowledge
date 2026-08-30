# SLO, SLI, and Error Budgets — Junior

<!-- level-focus -->
At junior level, turn one user promise into a measurable service-level indicator and objective.

## Start with the user journey

An **SLI** is a measured indicator, such as successful checkout requests divided by valid checkout requests. An **SLO** is its target: for example, 99.9% success over 30 days. The **error budget** is the allowed failure: 0.1% of eligible requests. An SLA is a customer contract; do not assume every internal SLO is one.

For checkout, exclude requests rejected because the user supplied invalid data, but include server errors and timeouts. Write the numerator and denominator before choosing a percentage.

## Apply it

1. Name one user action and its success event.
2. Define eligible requests and failure outcomes.
3. Calculate the allowed failures for a 30-day window.
4. Put the ratio and remaining budget on a dashboard.

## Verify your work

- A sample request can be explained as included or excluded.
- The ratio uses the same population in numerator and denominator.
- A teammate can calculate the budget from traffic volume.

## Review questions

- Why is a latency percentile an SLI rather than an SLO by itself?
- Which failures should checkout availability count?
