# Python Code Organization

> Put a change where its responsibility, dependencies, tests, and owner are easiest to understand.

```mermaid
flowchart LR
  Entry[entry point] --> App[capability package] --> Port[focused interface]
  Adapter[database / HTTP adapter] --> Port
```

Study [small project layout](junior.md), [capability boundaries](middle.md), [dependency direction](senior.md), and [organization-wide standards](professional.md). Practice by tracing one feature from entry point to external dependency.
