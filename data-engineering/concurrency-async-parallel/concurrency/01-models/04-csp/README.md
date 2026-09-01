# Communicating Sequential Processes

> CSP builds concurrent systems from sequential processes that synchronize through channels.

```mermaid
flowchart LR
    J[Junior: process and channel] --> M[Middle: select and cancel] --> S[Senior: prove liveness] --> P[Professional: runtime and algebra]
```

```mermaid
flowchart LR
    Read -->|records| Transform -->|clean rows| Write
```

| Level | Guide | You are done when |
|---|---|---|
| Junior | [Start](junior.md) | You can connect independent stages. |
| Middle | [Apply](middle.md) | You can implement cancellation and backpressure. |
| Senior | [Operate](senior.md) | You can prevent leaks, deadlock, and starvation. |
| Professional | [Design](professional.md) | You can reason about CSP semantics and runtimes. |

**Practice rule:** Every channel needs an owner, capacity, close rule, and cancellation path.

## Related

[Channels](../../02-primitives/05-channels/README.md) | [Actors](../03-actor-model/README.md)
