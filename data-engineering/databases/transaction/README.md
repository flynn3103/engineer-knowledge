# Transaction

> Covers Base and Eventual Consistency, Isolation Levels, Locking and Concurrency Control, MVCC, and Transactions and ACID.

## Topics

| Topic | What it covers |
|---|---|
| [Base and Eventual Consistency](base-and-eventual-consistency/) | BASE is ACID's counterpart for systems that chose availability and partition tolerance over strict consistency: Basically Available, Soft… |
| [Isolation Levels](isolation-levels/) | "Isolation" in ACID is a dial, not a switch. Each level trades correctness against concurrency by permitting a different set of anomalies —… |
| [Locking and Concurrency Control](locking-and-concurrency-control/) | When two transactions want the same row at the same time, something has to give: one waits, one aborts, or one reads a version that doesn't… |
| [MVCC](mvcc/) | Instead of making readers wait for writers, keep multiple versions of each row around and hand each transaction the version that matches… |
| [Transactions and ACID](transactions-and-acid/) | A transaction bundles multiple reads/writes into one unit that either fully happens or fully doesn't. ACID is the four-letter checklist for… |
