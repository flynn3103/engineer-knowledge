# On Production

> Reason about a system after it ships: size it correctly, prove it works, watch it run, ship changes to it safely, and keep it reliable, secure, and affordable under real traffic.

This roadmap picks up where design and implementation end. It follows the lifecycle of a system once it is live: estimate its scale before you build, test it so you know it works, understand its performance envelope, deploy and release it safely, watch it with monitoring and observability, diagnose it when something breaks, hold it to a reliability bar, defend it at scale, protect the data it holds, and keep it affordable.

> Deployment mechanics, orchestration, and network infrastructure now live in [Infrastructure](../../infrastructure/README.md).

```mermaid
flowchart LR
    Estimate["Estimate"] --> Test["Test"]
    Test --> Deploy["Deploy & Release"]
    Deploy --> Watch["Monitor & Observe"]
    Watch --> Diagnose["Diagnose"]
    Diagnose --> Harden["Reliability, Security, Cost"]
    Harden -.->|feeds back into| Estimate
```

## Learning path

| # | Section | Practice outcome |
|---|---|---|
| 01 | [Estimation](estimation/README.md) | Size a system from requirements before writing code. |
| 02 | [Testing](testing/README.md) | Choose the test level that actually catches the failure. |
| 03 | [Performance](performance/README.md) | Measure before optimizing, and protect the hot path from regression. |
| 04 | [Release](release/README.md) | Turn a built artifact into a traceable, reversible delivery. |
| 05 | [Monitoring](monitoring/README.md) | Know a system's health before a user reports it. |
| 06 | [Observability](observability/README.md) | Answer questions about the system you didn't know to ask in advance. |
| 07 | [SRE & Reliability](sre-reliability/README.md) | Own an error budget and respond to incidents deliberately. |
| 08 | [Security at Scale](security-at-scale/README.md) | Defend a system whose attack surface grows with its traffic. |
| 09 | [Data Privacy](data-privacy/README.md) | Handle user data under real legal and contractual obligations. |
| 10 | [Cost Efficiency](cost-efficiency/README.md) | Treat spend as a first-class engineering constraint. |

Every section contains a progressive four-level curriculum. Open a section to choose a topic and begin at the level that matches your current responsibility.

## Use this on a real system

1. Estimate the load and failure budget before committing to a design.
2. Write tests that would catch the failure you're most worried about.
3. Measure the hot path before changing it.
4. Deploy behind a rollback path you have actually exercised.
5. Confirm monitoring would have caught the last incident, not just this one.
6. When something breaks, diagnose from evidence, not assumption.
7. Feed what you learned back into the next estimate.

## Progression inside every published topic

| Level | Main responsibility |
|---|---|
| Junior | Run a known method correctly in a small, well-defined scope. |
| Middle | Choose boundaries, compare options, and verify an integrated flow. |
| Senior | Protect system invariants under load, failure, and change. |
| Professional | Align ownership, delivery, and measurable outcomes across teams. |
