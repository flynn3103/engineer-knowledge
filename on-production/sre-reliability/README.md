# SRE and Reliability

> Define reliable service from the user’s perspective, spend risk deliberately, and recover through practiced systems.

```mermaid
flowchart LR
    J[Junior: SLIs and incidents] --> M[Middle: SLOs and degradation] --> S[Senior: error budgets and resilience] --> P[Professional: reliability governance]
```

```mermaid
flowchart LR
    UserNeed --> SLI --> SLO --> ErrorBudget --> Decision --> Incident --> Learning
```

| Level | Guide | You are done when |
|---|---|---|
| Junior | [Operate one service](junior.md) | You can identify impact, follow a runbook, and validate recovery. |
| Middle | [Own an SLO](middle.md) | You can design degradation, shedding, and toil reduction. |
| Senior | [Manage reliability risk](senior.md) | You can use budgets, incidents, and recovery evidence. |
| Professional | [Govern reliability](professional.md) | You can align incentives and reliability across portfolios. |

## Practice rule

Define reliability as measurable user outcomes, not infrastructure uptime alone.

## Related

- [Monitoring](../monitoring/README.md)
- [Chaos Engineering](../chaos-engineering/README.md)
