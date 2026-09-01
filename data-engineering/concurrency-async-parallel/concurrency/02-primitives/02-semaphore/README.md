# Semaphore

> A semaphore uses permits to bound how many operations may use a resource concurrently.

```mermaid
flowchart LR
    J[Junior: permits] --> M[Middle: pools and cancellation] --> S[Senior: fairness and overload] --> P[Professional: resource governance]
```

```mermaid
flowchart LR
    Jobs --> Permit{3 permits} --> API[Limited API]
    API --> Release[Release permit]
```

| Level | Guide | You are done when |
|---|---|---|
| Junior | [Start](junior.md) | You can bound concurrent work. |
| Middle | [Apply](middle.md) | You can avoid permit leaks. |
| Senior | [Operate](senior.md) | You can handle fairness and overload. |
| Professional | [Design](professional.md) | You can govern resources across workloads. |

**Practice rule:** Acquire immediately before use and release exactly once in guaranteed cleanup.

## Related

[Mutex](../01-mutex/README.md) | [Condition variables](../03-condition-variables/README.md)
