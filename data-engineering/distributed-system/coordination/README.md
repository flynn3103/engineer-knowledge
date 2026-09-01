# Coordination

> Covers Atomic Commit 2PC 3PC TCC, Coordination Services, Exactly Once Semantics, Gossip Protocol, Idempotency Keys, Leader Election, Leases and Fencing, Optimistic vs Pessimistic Locking, Paxos, and Raft.

## Topics

| Topic | What it covers |
|---|---|
| [Atomic Commit 2PC 3PC TCC](atomic-commit-2pc-3pc-tcc/) | Three progressively more sophisticated attempts to make "all these databases commit together, or none of them do" work across a network —… |
| [Coordination Services](coordination-services/) | A small, purpose-built, highly-consistent cluster (etcd, ZooKeeper, Consul) that the rest of your distributed system leans on for the… |
| [Exactly Once Semantics](exactly-once-semantics/) | "Exactly-once" is one of the most misused phrases in distributed systems. True exactly-once delivery across a network is provably… |
| [Gossip Protocol](gossip-protocol/) | Instead of a central authority tracking cluster membership, every node periodically exchanges what it knows with a few random peers — and… |
| [Idempotency Keys](idempotency-keys/) | A unique identifier attached to a logical operation so that retrying it — deliberately or by accident, once or a thousand times — produces… |
| [Leader Election](leader-election/) | Make exactly one node in a cluster do the singleton job — and never let two nodes believe they're in charge at the same time. This is the… |
| [Leases and Fencing](leases-and-fencing/) | A lease is a time-bounded right to do something — hold a lock, act as leader — that expires automatically if not renewed. A fencing token… |
| [Optimistic vs Pessimistic Locking](optimistic-vs-pessimistic-locking/) | The same read-and-write concurrency choice covered for a single database in the Locking & Concurrency Control topic, now applied across… |
| [Paxos](paxos/) | The original proof that a group of unreliable nodes can agree on a single value even if some fail — the theoretical foundation almost every… |
| [Raft](raft/) | Consensus, designed to be understood. Raft decomposes the problem into leader election, log replication, and safety — each explained and… |
