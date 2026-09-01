# Broker Selection - Middle
```mermaid
flowchart TD
 Need{Primary need}
 Need -->|long replay and analytics| Kafka
 Need -->|rich routing and work queues| RabbitMQ
 Need -->|simple low-latency messaging| JetStream
```
Build one adapter contract and run identical payload, producer, consumer, acknowledgement, replication, and failure tests. Record throughput, p50/p99, redelivery, ordering, recovery time, and operator effort.
## Test yourself
1. What must the common adapter expose?
2. Why test slow consumers?
3. Which guarantees cannot one generic API hide?
Continue to [`senior.md`](senior.md).
