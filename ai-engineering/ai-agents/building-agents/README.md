# Building Agents

> Build the smallest complete loop first; add frameworks only for complexity you can name.

```mermaid
flowchart LR
    J[Junior<br/>manual loop] --> M[Middle<br/>typed provider adapter]
    M --> S[Senior<br/>resilience and deployment]
    S --> P[Professional<br/>runtime and fleet design]
```

```mermaid
flowchart TD
    API[Application API] --> R[Agent runner]
    R --> P[Model provider adapter]
    R --> T[Tool registry]
    R --> S[State store]
    R --> O[Tracing and evaluation]
    P --> L[LLM API]
    T --> X[External systems]
```

## Levels

| Level | Guide | You are done when... |
|---|---|---|
| Junior | [junior.md](junior.md) | You can implement and trace a small tool-using loop with raw SDK calls |
| Middle | [middle.md](middle.md) | You can separate provider events, tool execution, and application state |
| Senior | [senior.md](senior.md) | You can deploy with retries, idempotency, budgets, persistence, and observability |
| Professional | [professional.md](professional.md) | You can design a provider-neutral runtime and operate it across a fleet |

## Practice rule

Keep one golden end-to-end trace for the raw SDK implementation. Use it to verify every abstraction or framework migration.

## Related

- [AI Agents 101](../ai-agents-101/)
- [Tools and Actions](../tools-actions/)
- [Agent Architectures](../agent-architectures/)
- [Evaluation and Testing](../evaluation-and-testing/)
