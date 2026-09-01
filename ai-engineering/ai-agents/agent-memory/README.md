# Agent Memory

> Agent memory is selective state: what to retain, retrieve, update, and deliberately forget.

```mermaid
flowchart LR
    J[Junior<br/>working vs long-term] --> M[Middle<br/>write and retrieve]
    M --> S[Senior<br/>quality, privacy, lifecycle]
    S --> P[Professional<br/>storage and retrieval internals]
```

```mermaid
flowchart TD
    I[Interaction] --> W[Working context]
    W --> X[Memory extractor]
    X --> E[(Episodic store)]
    X --> S[(Semantic/profile store)]
    Q[New request] --> R[Retriever]
    E --> R
    S --> R
    R --> W
```

## Levels

| Level | Guide | You are done when... |
|---|---|---|
| Junior | [junior.md](junior.md) | You can distinguish context history, episodic memory, and semantic memory |
| Middle | [middle.md](middle.md) | You can implement explicit memory writes and relevance-based retrieval |
| Senior | [senior.md](senior.md) | You can prevent stale, poisoned, private, or contradictory memories from driving behavior |
| Professional | [professional.md](professional.md) | You can design memory storage, indexing, lifecycle, and operations at scale |

## Practice rule

Do not store every message. Define why each memory will help a future decision, who owns it, and when it expires.

## Related

- [AI Agents 101](../ai-agents-101/)
- [Agent Architectures](../agent-architectures/)
- [Evaluation and Testing](../evaluation-and-testing/)
- [Security and Ethics](../security-ethics/)
