# DLQ and Retry - Professional
Kafka retry topics trade partition order for independent delay; RabbitMQ dead-letter exchanges and TTL queues provide routing-based delay; SQS exposes visibility timeouts and redrive policies.
At scale, amplification and DLQ retention dominate. Dashboard attempts/original, retry age, DLQ bytes, replay rate, and downstream saturation.
## Best practices
- Use stable event identity across every hop.
- Bound attempts, elapsed time, and retained bytes.
- Separate inspect, repair, replay, and audit permissions.
- Capacity-test dependency outage plus recovery surge.
```text
retry = transient + budget + backoff
DLQ = durable quarantine + owner + replay control
```
## Test yourself
1. How would you preserve order for one financial account?
2. What prevents replay from causing a second outage?
3. Which SLO makes DLQ neglect visible?
## Further reading
- Kafka retry and delivery semantics documentation.
- AWS SQS dead-letter queue documentation.
- Enterprise Integration Patterns, *Dead Letter Channel*.
