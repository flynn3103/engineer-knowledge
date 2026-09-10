# SRE and Reliability

> Define reliable service from the user's perspective, trace and measure a live system with the right signal for the right question, spend risk deliberately, and recover through practiced systems.

```mermaid
flowchart LR
    J[Junior: signals and first response] --> M[Middle: instrument and budget]
    M --> S[Senior: incident command and audit] --> P[Professional: platform governance]
```

```mermaid
flowchart LR
    UserNeed --> SLI --> SLO --> ErrorBudget --> Decision --> Incident --> Telemetry --> Learning --> UserNeed
```

This topic covers both halves of running a system in production: the **SRE discipline** (SLIs, SLOs, error budgets, incident response, postmortems) and the **observability tooling** it runs on (logs, metrics, traces, profiles, crash reports, sampling). It is the operational counterpart to [Debug-Thinking](../../engineering-thinking/08-debug-thinking/README.md), which covers the reasoning process — pattern recognition, bisection, hypothesis testing — you apply *through* this tooling.

| Level | Guide | You are done when |
|---|---|---|
| Junior | [First incident response](junior.md) | You can identify impact, follow a runbook, choose the right signal for a question, and verify recovery from the user path. |
| Middle | [Instrument and budget](middle.md) | You can instrument a service with RED/USE metrics, propagate trace context, use error-budget burn to prioritize work, and reduce toil. |
| Senior | [Incident command and audit](senior.md) | You can own SLOs across dependencies, lead incident roles, design telemetry for degraded state, and run blameless postmortems that produce durable fixes. |
| Professional | [Platform governance](professional.md) | You can govern SLOs and telemetry cost across a shared platform, and design multi-window alerting and observability infrastructure at scale. |

## Practice rule

Define reliability as measurable user outcomes, not infrastructure uptime alone. Pick the observability signal — log, metric, trace, or profile — that answers the specific question you're asking, not the one that's easiest to add.

## Related

- [Debug-Thinking](../../engineering-thinking/08-debug-thinking/README.md) — the reasoning process this topic's tooling supports.
- [Performance](../performance/README.md) — profiling and hot-path measurement this topic's telemetry feeds into.
- [Release](../release/README.md) — the deploys whose blast radius this topic's SLOs and error budgets bound.
