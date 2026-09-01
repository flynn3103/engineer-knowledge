# STM - Junior

Software transactional memory lets several shared-memory changes commit together. If another transaction changed a value you read, your work retries.

```mermaid
sequenceDiagram
    participant A as Worker A
    participant B as Worker B
    participant S as Transactional state
    A->>S: read version 4
    B->>S: commit version 5
    A->>S: commit based on 4
    S-->>A: conflict; retry
```

Think of updating an in-memory batch count and total together. Both become visible or neither does. Do not send network requests, write files, or log non-idempotent events inside a transaction because retries can repeat them.

Continue to [`middle.md`](middle.md).

## Test yourself

1. Why can an STM transaction run more than once?
2. Which operations must stay outside it?
3. What advantage does one atomic block have over several locks?
