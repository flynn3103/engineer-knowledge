# Schema Evolution - Junior
Events outlive deployments. Renaming or changing a field can break old consumers and make historical records unreadable.
```mermaid
sequenceDiagram
 participant P as New producer
 participant K as Kafka
 participant C as Old consumer
 P->>K: amount as string
 K->>C: event
 Note over C: expected numeric amount; fails
```
A schema registry stores versioned contracts and blocks incompatible changes before production.
## Test yourself
1. Why are events longer-lived than API requests?
2. Who can a producer change break?
3. Why keep schema versions?
Continue to [`middle.md`](middle.md).
