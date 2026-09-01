# Event Replay - Professional
Kafka offsets provide partition-local progress; event-sourced stores such as EventStoreDB organize streams by aggregate; Elasticsearch aliases support atomic read-model swaps.
At billion-event scale, source read bandwidth, sink write amplification, compaction, and live-tail convergence dominate. Dashboard events/s, bytes/s, lag derivative, error classes, checksum drift, and cutover readiness.
## Best practices
- Separate pure projection logic from side effects.
- Version events and replay code for the full retention horizon.
- Reserve capacity for live traffic and emergency rollback.
- Prove convergence and semantic equivalence before cutover.
```text
rebuild history -> follow live tail -> verify -> atomic swap
```
## Test yourself
1. How would you estimate catch-up time under continuing writes?
2. What proof supports deletion of the old projection?
3. How does log compaction change replay guarantees?
## Further reading
- Fowler, *Event Sourcing*.
- Kafka log and offset documentation.
- EventStoreDB projection documentation.
