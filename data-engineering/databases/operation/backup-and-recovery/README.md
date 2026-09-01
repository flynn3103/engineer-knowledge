# Backup & Recovery

> A backup you've never restored is a hypothesis, not a backup. This topic is
> about the mechanisms (full/incremental/WAL-based) and the two numbers that
> actually matter when something breaks: how much data you can lose (RPO) and
> how long you can be down (RTO).

```mermaid
flowchart LR
    Junior["Junior: full vs. incremental backups"] --> Middle["Middle: point-in-time recovery via WAL replay"]
    Middle --> Senior["Senior: RPO/RTO, backup testing, corruption vs. deletion"]
    Senior --> Professional["Professional: backup strategy for pipeline state, not just the database"]
```

```mermaid
flowchart LR
    Full["Full backup\n(Sunday)"] --> Inc1["Incremental\n(Monday)"] --> Inc2["Incremental\n(Tuesday)"] --> WAL["WAL/log archive\n(continuous)"]
    WAL -.enables point-in-time\nrecovery to ANY second.-> Restore["Restore to 2:47pm Wednesday"]
```

## Choose a level

| Level | Guide | You are done when |
|---|---|---|
| Junior | [Full vs. incremental backups](junior.md) | You can explain the storage/restore-speed trade-off between full and incremental backups. |
| Middle | [Point-in-time recovery](middle.md) | You can explain how a base backup plus WAL archive lets you restore to any specific second. |
| Senior | [RPO, RTO, and testing backups](senior.md) | You can define RPO/RTO for a real system and explain why an untested backup is not a safety net. |
| Professional | [Backing up pipeline state, not just the DB](professional.md) | You can design a recovery plan covering Kafka offsets, checkpoint state, and orchestrator metadata — not just the database. |

## Practice rule

Pick a backup your team currently relies on and ask: "when was the last time
someone actually restored from this, end to end, and measured how long it
took?" If the honest answer is "never," you don't have a tested recovery
plan — you have an unverified assumption.

## Related

- [MVCC](../../transaction/mvcc/README.md)
- [Replication](../../scaling/replication/README.md)
- [Transactions & ACID](../../transaction/transactions-and-acid/README.md)
