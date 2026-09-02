# Production Monitoring

> Detect user impact and unsafe system state early enough for a human or automation to act.

```mermaid
flowchart LR
    J[Junior: health signals] --> M[Middle: dashboards and alerts] --> S[Senior: service monitoring] --> P[Professional: fleet monitoring]
```

```mermaid
flowchart LR
    Instrument --> Collect --> Aggregate --> Visualize --> Alert --> Respond --> Improve
```

| Level | Guide | You are done when |
|---|---|---|
| Junior | [Monitor one service](junior.md) | You can distinguish availability, health, and performance. |
| Middle | [Build actionable alerts](middle.md) | You can create dashboards, synthetic checks, and useful thresholds. |
| Senior | [Monitor user outcomes](senior.md) | You can align alerts with SLOs, security, and capacity. |
| Professional | [Govern fleet monitoring](professional.md) | You can operate scalable, reliable monitoring systems. |

## Practice rule

Every alert needs an owner, user impact, action, urgency, and runbook. Otherwise it is a dashboard query, not an alert.

## Related

- [Observability](../observability/README.md)
- [SRE & Reliability](../sre-reliability/README.md)
