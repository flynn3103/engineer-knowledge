# Window Computation - Junior

> Which minute owns a mobile purchase created at 10:01 but delivered at 10:08?

A naive processor groups by arrival time. Retries, offline clients, and Kafka
backlogs then move business events into later buckets even though their event
timestamps did not change.

```mermaid
sequenceDiagram
    participant M as Mobile client
    participant K as Kafka
    participant P as Processor
    M->>M: purchase at 10:01
    Note over M: offline for 7 minutes
    M->>K: send at 10:08
    K->>P: arrives at 10:08
    Note over P: processing-time bucket says 10:08; event-time says 10:01
```

- **Processing time** is the processor clock when a record runs.
- **Event time** is when the source says the event occurred.
- **Ingestion time** is when infrastructure first accepted it.

Event time gives replay-stable business buckets, but the processor cannot know
immediately whether an older event is still coming. Waiting forever gives perfect
completeness and no timely output. Emitting immediately gives low latency and
results that may need correction.

## Test yourself

1. Which time domain keeps the purchase in the 10:01 bucket after replay?
2. Why can the processor never know instantly that all events arrived?
3. What trade-off appears between result latency and completeness?

Continue to [`middle.md`](middle.md).
