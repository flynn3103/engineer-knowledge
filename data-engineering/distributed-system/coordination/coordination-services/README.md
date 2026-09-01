# Coordination Services

> A small, purpose-built, highly-consistent cluster (etcd, ZooKeeper,
> Consul) that the rest of your distributed system leans on for the things
> ordinary databases aren't built for: leader election, distributed locks,
> service discovery, and configuration that must never be read
> inconsistently.

```mermaid
flowchart LR
    Junior["Junior: why you need a dedicated service for this, not just any database"] --> Middle["Middle: the core primitives - watches, sessions, ephemeral nodes"]
    Senior["Senior: sizing and failure modes of the coordination cluster itself"]
    Middle --> Senior --> Professional["Professional: etcd/ZooKeeper internals and operating them at scale"]
```

```mermaid
flowchart LR
    App1[App instance 1] --> Coord["Coordination service\n(etcd/ZooKeeper cluster,\nRaft/ZAB-backed)"]
    App2[App instance 2] --> Coord
    App3[App instance 3] --> Coord
    Coord --> Uses["Leader election, locks,\nservice discovery,\nshared config"]
```

## Choose a level

| Level | Guide | You are done when |
|---|---|---|
| Junior | [Why a dedicated service](junior.md) | You can explain why an ordinary database (even a strongly consistent one) is usually the wrong tool for this job. |
| Middle | [Watches, sessions, ephemeral nodes](middle.md) | You can explain how these three primitives combine to implement leader election or service discovery. |
| Senior | [Sizing and failure modes](senior.md) | You can explain why the coordination cluster itself becomes a single point of failure if under-provisioned. |
| Professional | [etcd/ZooKeeper internals at scale](professional.md) | You can explain the consensus protocol underneath and real operational limits (watch storms, request rate ceilings). |

## Practice rule

Before reaching for a coordination service, ask: "do I actually need
linearizable, strongly-consistent reads and writes for this, or would
eventual consistency (a regular cache, a regular database) be fine?" A
coordination service is deliberately low-throughput and expensive per
operation, in exchange for consistency guarantees most application data
doesn't need.

## Related

- [Leader Election](../leader-election/README.md)
- [Gossip Protocol](../gossip-protocol/README.md)
- [Leases & Fencing](../leases-and-fencing/README.md)
