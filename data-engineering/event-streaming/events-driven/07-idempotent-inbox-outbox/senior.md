# Inbox and Outbox - Senior
| Failure or mistake | Control |
|---|---|
| relay marks before publish | publish first, then retry-safe mark |
| unstable event ID | persist ID with intent |
| effect outside inbox transaction | atomic inbox plus effect |
| premature dedup expiry | retention/replay-based TTL |
| stuck outbox | age and reconciliation alert |
Prove `distinct effects == distinct intents` under crashes after every boundary. Monitor oldest outbox, publish attempts, duplicate ratio, inbox growth, and reconciliation drift.
## Test yourself
1. How is dedup retention chosen?
2. What crash creates relay duplicates?
3. What does reconciliation compare?
Continue to [`professional.md`](professional.md).
