# Object-Oriented Design

> Assign behavior to cohesive objects so domain rules stay local and change does not spread through the system.

```mermaid
flowchart LR
    J[Junior: objects and responsibility] --> M[Middle: coupling and SOLID]
    M --> S[Senior: domain boundaries]
    S --> P[Professional: evolution and governance]
```

```mermaid
flowchart LR
    Requirement --> Responsibility --> Collaborator --> Object
    Object --> Message --> Behavior
    Behavior --> Invariant
```

This guide consolidates KISS, YAGNI, separation of concerns, cohesion, coupling, connascence, composition, SOLID, object thinking, GRASP, modeling, concurrency, extension, and common OO smells.

| Level | Guide | You are done when |
|---|---|---|
| Junior | [Model behavior](junior.md) | You can place a rule with the state it protects. |
| Middle | [Manage collaboration](middle.md) | You can use cohesion, coupling, composition, and SOLID as trade-offs. |
| Senior | [Design domain boundaries](senior.md) | You can protect invariants under concurrency and evolution. |
| Professional | [Govern object models](professional.md) | You can guide framework, API, and domain evolution across teams. |

## Practice rule

Ask which object is responsible for deciding and protecting the rule. Prefer telling that object what outcome is needed over extracting its data and deciding elsewhere.

## Related

- [Legacy Code](../legacy-code/README.md)
- [Code Review](../code-review/README.md)
