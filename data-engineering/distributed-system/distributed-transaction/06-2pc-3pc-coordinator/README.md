# Two-Phase and Three-Phase Commit

> Atomic commit gives several participants one durable decision, at the cost of coordination and blocking.

```mermaid
flowchart LR
    J[Junior: why atomic commit] --> M[Middle: prepare and decide] --> S[Senior: in-doubt failures] --> P[Professional: scale and recovery]
```
```mermaid
flowchart LR
    Coordinator --> Prepare --> Participants --> Decision[Commit or abort]
```

| Level | Guide | You are done when |
|---|---|---|
| Junior | [Definition and why](junior.md) | You can explain why sequential commits fail. |
| Middle | [How it works](middle.md) | You can trace durable prepare and decision ordering. |
| Senior | [Failures and mistakes](senior.md) | You can resolve in-doubt transactions safely. |
| Professional | [Best practices and scale](professional.md) | You can govern atomic commit at scale. |

**Practice rule:** After prepare, never guess the global decision from a timeout.

## Related
[Saga](../07-saga-orchestration-vs-choreography/README.md) | [TCC](../08-tcc-try-confirm-cancel/README.md)
