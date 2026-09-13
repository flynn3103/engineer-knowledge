# Data Privacy — Junior

Classify direct identifiers, quasi-identifiers, sensitive attributes, credentials, and operational metadata. Minimize collection and redact logs, traces, errors, and test fixtures.

```mermaid
sequenceDiagram
    User->>Service: personal data
    Service->>Policy: purpose and consent
    Service->>Storage: encrypted minimal record
    Service->>Audit: actor and action, no secret value
```

## Test yourself

1. Which field is a quasi-identifier?
2. Why is production data unsafe in tests?
3. What belongs in an audit event?
4. How is deletion verified?

Continue to [`middle.md`](middle.md).
