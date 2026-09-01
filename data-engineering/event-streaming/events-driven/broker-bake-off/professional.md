# Broker Selection - Professional
Kafka replicates partition logs with leader/follower ISR; RabbitMQ quorum queues use Raft; JetStream streams use Raft groups for metadata and replicated messages.
At scale, partition/queue count, disk IOPS, replication traffic, rebalancing, and operator toil dominate. Dashboard durability health, p99, backlog age, disk headroom, recovery, and unavailable partitions/queues.
## Best practices
- Write a workload and failure contract before benchmarking.
- Separate product semantics from client-library behavior.
- Price storage, network, staffing, upgrades, and recovery.
- Re-run selection tests after major version changes.
```text
best broker = required semantics + proven failure behavior + operable cost
```
## Test yourself
1. How do quorum design and partition count affect cost?
2. What evidence supports standardizing on two brokers?
3. Which benchmark result predicts incident recovery?
## Further reading
- Kafka, RabbitMQ quorum queue, and NATS JetStream design docs.
- Kreps et al., *Kafka: a Distributed Messaging System for Log Processing*.
