# Python HTTP APIs — Middle

Keep transport code thin:

```mermaid
sequenceDiagram
    Client->>Handler: request
    Handler->>UseCase: validated command
    UseCase->>Store: read or write
    UseCase-->>Handler: result or domain error
    Handler-->>Client: response
```

Use schemas for validation and serialization. Set request timeouts for outbound calls. Paginate collections, authenticate before sensitive work, and make write requests idempotent when clients can retry.
