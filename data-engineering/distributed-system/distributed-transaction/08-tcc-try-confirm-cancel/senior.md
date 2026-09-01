# TCC: Try, Confirm, Cancel - Senior

Reservation isolation and expiry determine whether TCC prevents oversell without wasting capacity.

| Failure | Control |
|---|---|
| Cancel before Try | tombstone/null compensation |
| Confirm after Cancel | terminal-state rejection |
| coordinator crash | durable decision and redrive |
| abandoned reservation | TTL plus decision reconciliation |
| concurrent Try | conditional capacity update |

Monitor reservation age, phase-two retries, unavailable capacity, conflicting transitions, and coordinator backlog. Do not auto-cancel after TTL if a durable Confirm decision may already exist.

## Test yourself

1. Why can TTL cleanup conflict with Confirm?
2. How is oversell prevented atomically?
3. When is TCC too invasive for participants?

Continue to [`professional.md`](professional.md).
