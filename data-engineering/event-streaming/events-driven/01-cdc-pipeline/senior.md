# CDC Pipeline - Senior
| Failure or mistake | Safe response |
|---|---|
| connector stalls | alert on retained WAL bytes and disk headroom |
| event redelivered | versioned idempotent sink |
| schema changes | compatible rollout and quarantine |
| snapshot restarts | resume supported snapshot state |
| hot key | preserve order while scaling other partitions |
Test connector death during snapshot and streaming, sink lag, schema changes, and TOAST-heavy updates. Reconcile source rows against sink state rather than trusting offsets alone.
## Test yourself
1. How can CDC fill the source disk?
2. What proves no changes were lost?
3. Why is offset commit alone insufficient?
Continue to [`professional.md`](professional.md).
