# Scaling

> Covers Database Federation, Partitioning and Sharding, and Replication.

## Topics

| Topic | What it covers |
|---|---|
| [Database Federation](database-federation/) | Split a database by function (orders, users, inventory) rather than by key range — each service gets its own database. Solves a different… |
| [Partitioning and Sharding](partitioning-and-sharding/) | Split one logical dataset across multiple physical nodes so no single machine has to store or serve all of it. The mechanism that lets a… |
| [Replication](replication/) | Keep copies of the same data on multiple nodes so the system survives a node failure and can serve more read traffic than one machine could… |
