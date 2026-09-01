# Inbox and Outbox - Professional
Debezium Outbox Event Router publishes committed outbox rows through WAL; Kafka transactions atomically bind Kafka records and offsets but not arbitrary databases; PostgreSQL unique indexes enforce inbox identity.
At scale, outbox table/index bloat, relay lag, dedup storage, and hot aggregate ordering dominate. Dashboard intent-to-publish age, duplicates, cleanup lag, inbox conflicts, and end-to-end reconciliation.
## Best practices
- Define stable message identity and aggregate ordering key.
- Partition and clean tables without outrunning replay requirements.
- Make reconciliation continuous, not incident-only.
- Load-test relay catch-up after broker outage.
```text
outbox closes DB -> broker loss gap
inbox closes broker -> DB duplicate-effect gap
```
## Test yourself
1. When can Kafka transactions replace an inbox?
2. How would you partition a billion-row dedup store?
3. What proves cleanup is safe?
## Further reading
- Richardson, *Transactional Outbox* pattern.
- Debezium Outbox Event Router documentation.
- Kafka transactions and exactly-once semantics documentation.
