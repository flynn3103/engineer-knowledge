# Consumer Autoscaling - Professional
KEDA exposes Kafka lag as an external metric; HPA applies tolerance and stabilization; Kafka's cooperative-sticky assignor incrementally transfers partitions.
At scale, metric delay, rebalance cost, cold starts, partition skew, and downstream quotas dominate. Dashboard control-loop delay, desired/current replicas, drain ETA, partition lag distribution, rebalances, and downstream saturation.
## Best practices
- Scale from SLO-based drain time and measured service rate.
- Include partition ceiling, downstream capacity, and startup delay.
- Use hysteresis and conservative scale-down.
- Pre-scale predictable peaks when reactive delay is too long.
```text
required capacity = arrival rate + backlog / target drain time
useful replicas <= active partitions
```
## Test yourself
1. How would you tune a loop with five-minute pod startup?
2. What changes when one partition owns most lag?
3. How do downstream quotas constrain desired replicas?
## Further reading
- KEDA Kafka scaler documentation.
- Kubernetes HPA algorithm documentation.
- Kafka consumer group protocol and assignor documentation.
