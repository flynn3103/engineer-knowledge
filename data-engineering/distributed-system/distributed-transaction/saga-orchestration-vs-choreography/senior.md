# Saga: Orchestration vs Choreography - Senior

Sagas expose intermediate state, duplicate messages, semantic races, and failed compensation.

| Risk | Control |
|---|---|
| duplicate command | inbox/dedup key |
| stale concurrent Saga | semantic lock or version check |
| lost event | transactional outbox |
| compensation failure | durable retry and manual repair |
| invisible choreography | correlation view and tracing |

Monitor Saga age by state, retry count, compensation backlog, stuck pivots, and correlation completeness. Rehearse code upgrades while old Sagas are still running.

## Test yourself

1. How does a semantic lock prevent conflicting Sagas?
2. Which states require operator action?
3. When is orchestration easier to operate?

Continue to [`professional.md`](professional.md).
