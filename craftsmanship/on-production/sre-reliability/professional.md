# SRE and Reliability — Professional

Google SRE formalized error budgets; multi-window burn-rate alerts detect fast and slow consumption; incident command separates coordination from diagnosis. At scale, inconsistent SLI definitions, shared-platform ownership, and capacity coupling dominate.

## Design and operations checklist

1. Tie SLOs to user journeys.
2. Assign risk acceptance and incident authority.
3. Budget overload and degraded modes.
4. Rehearse recovery and regional failure.
5. Track toil and postmortem action outcomes.

```text
USER NEED -> SLI -> SLO -> BUDGET -> RISK DECISION -> INCIDENT -> LEARNING
```

## Test yourself

1. Design SLO governance for a shared platform.
2. How can an error budget be gamed?
3. Which recovery evidence belongs in design review?
4. How do you fund reliability across products?

## Further reading

- Google, *Site Reliability Engineering*.
- Google, *The Site Reliability Workbook*.
- Richard Cook, “How Complex Systems Fail.”
