# Distributed Locks with Fencing - Professional

Lock correctness depends on the lease model, the token's total order, and atomic enforcement at the mutation boundary.

## Real systems

- ZooKeeper recipes use ephemeral sequential znodes; sequence numbers order contenders and watches avoid polling.
- etcd's Raft-backed revision is monotonic across committed writes; leases revoke attached keys but do not stop paused clients.
- Redis `SET NX PX` provides conditional acquisition on one primary, while failover and Redlock assumptions require separate safety analysis.
- Google Chubby uses sequencers so servers can reject operations from obsolete lock holders.

At 10x contention, watch queues and lease traffic dominate. At 100x, one consensus key becomes a serialization bottleneck. Dashboard acquisition/hold latency, lease expiry, token gaps, rejected stale operations, session churn, and quorum health. A runbook must fence or stop writers before repairing the lock service.

## Design and operations checklist

- State the safety property independently of the lock API.
- Prove tokens never decrease or repeat after failover.
- Enforce tokens atomically with each protected write.
- Bound lease, wait, and operation durations without equating timeouts with safety.
- Reproduce stale-holder writes in chaos tests.

```text
lease: who may try now
fence: which owner the resource will still trust
```

## Test yourself

1. Can a wall-clock timestamp safely replace a consensus revision?
2. How would you migrate a resource that cannot store the highest token?
3. Which failure assumptions does a multi-primary lock require?

## Further reading

- Martin Kleppmann, *How to Do Distributed Locking*.
- ZooKeeper Recipes and Solutions: Locks.
- Burrows, *The Chubby Lock Service for Loosely-Coupled Distributed Systems*.
