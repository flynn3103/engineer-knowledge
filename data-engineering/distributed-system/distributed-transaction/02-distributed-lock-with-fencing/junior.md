# Distributed Locks with Fencing - Junior

A distributed lock tries to let one worker use a shared resource at a time. A data pipeline may lock `daily-report/customer-42` before writing its output.

```mermaid
sequenceDiagram
    participant A as Worker A
    participant L as Lock with TTL
    participant B as Worker B
    participant R as Report
    A->>L: acquire
    Note over A: long GC pause
    L-->>B: TTL expired; acquire
    B->>R: write new report
    A->>R: wakes and overwrites report
```

The naive rule, "if I acquired the lock, I may write," breaks because a paused worker cannot know its lease expired. Renewal helps availability but cannot remove every pause or network delay. The protected resource needs a way to reject stale owners.

## Test yourself

1. Why can two workers both believe they own one lock?
2. Why is a random owner ID useful during release?
3. Why can TTL renewal not prove ownership at write time?

Continue to [`middle.md`](middle.md).
