# Load Balancers

> Route traffic only to capable targets and prove that failure detection and recovery behave as designed.

## Topics

| # | Topic | Practice outcome |
|---|---|---|
| 01 | [Load Balancer vs Reverse Proxy](01-lb-vs-reverse-proxy/junior.md) | Place each responsibility on the traffic path. |
| 02 | [Load-Balancing Algorithms](02-load-balancing-algorithms/junior.md) | Select an algorithm from workload evidence. |
| 03 | [Layer 4 Load Balancing](03-layer-4-load-balancing/junior.md) | Route connections without application inspection. |
| 04 | [Layer 7 Load Balancing](04-layer-7-load-balancing/junior.md) | Route requests by application data. |
| 05 | [Health Checks and Failover](05-health-checks-and-failover/junior.md) | Detect failure without creating flapping or overload. |
| 06 | [Horizontal Scaling](06-horizontal-scaling/junior.md) | Remove local state that prevents safe scale-out. |
| 07 | [Global Server Load Balancing](07-global-server-load-balancing/junior.md) | Route regions and define failover authority. |

## Practice loop

Predict which target receives a controlled request, make one target unhealthy, and verify removal, client behavior, and recovery timing.
