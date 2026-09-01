# Broker Selection - Senior
| Mistake | Better test |
|---|---|
| benchmark defaults | match durability and batching |
| average latency only | p99 during failure |
| ignore retention | replay and disk pressure |
| ignore operations | upgrade, rebalance, restore |
| one synthetic workload | representative payload and skew |
Evaluate ordering scope, backpressure, redelivery, partition/queue limits, client maturity, and team competence.
## Test yourself
1. Why can batching distort latency comparisons?
2. What failure recovery should be timed?
3. Which workload facts dominate broker choice?
Continue to [`professional.md`](professional.md).
