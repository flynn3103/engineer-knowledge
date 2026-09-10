# High-Level Design

> Define system architecture: components, data flow, and integration points. High-level design answers "what are the major pieces and how do they interact?"

```mermaid
flowchart LR
    J[Junior: Draw system components] --> M[Middle: Design component interactions] --> S[Senior: Manage system boundaries] --> P[Professional: Evolve architecture with teams]
```

```mermaid
flowchart LR
    Requirements --> Components --> Interfaces --> DataFlow --> Deployment
```

| Level | Guide | You are done when |
|---|---|---|
| Junior | [Draw system components](junior.md) | You can identify major components and describe their responsibilities. |
| Middle | [Design component interactions](middle.md) | You can define interfaces, data flow, and integration patterns. |
| Senior | [Manage system boundaries](senior.md) | You can set ownership, handle failure modes, and plan evolution. |
| Professional | [Evolve architecture with teams](professional.md) | You can decompose architecture into team-owned services and track migration. |

## Practice rule

Separate concerns: each component should have a clear responsibility. Make interfaces explicit. Show data flow, not just component names.

## Related

- [Functional Requirements](../functional-requirements/README.md)
- [Low-Level Design](../low-level-design/README.md)
- [Non-Functional Requirements](../non-functional-requirements/README.md)
