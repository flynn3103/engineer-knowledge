# Consumer Autoscaling - Middle
Estimate required replicas from arrival rate, per-replica processing rate, backlog, and target drain time.
```mermaid
flowchart LR
 Metrics[Lag and throughput] --> Controller[KEDA/HPA] --> Desired[Desired replicas] --> Group[Rebalance group]
```
Cap replicas at useful partition count, smooth noisy measurements, and keep headroom. Scale down only after cooldown and graceful offset commit. Cooperative-sticky assignment reduces movement compared with eager rebalance.
## Test yourself
1. Which rates determine drain time?
2. Why cap at partition count?
3. How does cooperative rebalancing help?
Continue to [`senior.md`](senior.md).
