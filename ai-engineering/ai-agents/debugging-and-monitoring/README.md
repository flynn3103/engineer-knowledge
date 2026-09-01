# Debugging and Monitoring

> Debug an agent as a trace of decisions and effects, not as one final string.

```mermaid
flowchart LR
    J[Junior<br/>structured events] --> M[Middle<br/>distributed traces]
    M --> S[Senior<br/>SLOs and incidents]
    S --> P[Professional<br/>telemetry pipelines]
```

```mermaid
flowchart TD
    R[Agent run] --> M[Model spans]
    R --> T[Tool spans]
    R --> P[Policy spans]
    R --> S[State spans]
    M --> O[Trace]
    T --> O
    P --> O
    S --> O
    O --> D[Metrics, logs, evaluation]
```

## Levels

| Level | Guide | You are done when... |
|---|---|---|
| Junior | [junior.md](junior.md) | You can reconstruct a failed run from correlated structured events |
| Middle | [middle.md](middle.md) | You can instrument model, tool, policy, and state spans safely |
| Senior | [senior.md](senior.md) | You can define SLOs, alerts, runbooks, and rollback signals |
| Professional | [professional.md](professional.md) | You can operate high-volume telemetry without leaking data or losing causality |

## Practice rule

Record identifiers, versions, timings, outcomes, and hashes by default; record sensitive content only through explicit, controlled sampling.

## Related

- [Building Agents](../building-agents/)
- [Evaluation and Testing](../evaluation-and-testing/)
- [Security and Ethics](../security-ethics/)
