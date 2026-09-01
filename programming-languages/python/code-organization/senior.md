# Python Code Organization — Senior

Architecture should make dependency direction visible.

```mermaid
flowchart LR
    API[API / worker] --> App[application use case]
    App --> Domain[domain rules]
    App --> Ports[ports]
    Adapters[database, queue, HTTP] --> Ports
```

The composition root wires concrete adapters. Domain rules do not import a web framework or ORM. Split a package only when ownership, release cadence, or a stable boundary requires it.
