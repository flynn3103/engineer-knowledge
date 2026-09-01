# Operation

> Covers Backup and Recovery, Caching, Connection Pooling, OLTP vs OLAP, Stored Procedures and Triggers, and Views.

## Topics

| Topic | What it covers |
|---|---|
| [Backup and Recovery](backup-and-recovery/) | A backup you've never restored is a hypothesis, not a backup. This topic is about the mechanisms (full/incremental/WAL-based) and the two… |
| [Caching](caching/) | Covers Cache Aside, Cache Invalidation, Cache Stampede and Hot Keys, Eviction Policies, Refresh Ahead, Types of Caching, Write Behind, and… |
| [Connection Pooling](connection-pooling/) | Opening a database connection is expensive — TCP handshake, TLS, auth, session setup. A connection pool reuses a small set of already-open… |
| [OLTP vs OLAP](oltp-vs-olap/) | Transactional systems and analytical systems want opposite things from a database engine. Confusing the two — running heavy analytics on… |
| [Stored Procedures and Triggers](stored-procedures-and-triggers/) | Code that lives inside the database, running close to the data instead of in application/pipeline code. Powerful for atomicity and… |
| [Views](views/) | A view is a saved query that looks like a table. A materialized view is a saved query that *is* a table, refreshed on a schedule you… |
