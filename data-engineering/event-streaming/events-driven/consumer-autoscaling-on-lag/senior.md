# Consumer Autoscaling - Senior
| Failure or mistake | Control |
|---|---|
| react to one sample | stabilization window |
| scale on total lag only | age and lag derivative |
| rapid scale cycles | hysteresis and cooldown |
| scale down mid-work | graceful drain and commit |
| more replicas than partitions | hard useful ceiling |
Monitor oldest-event age, arrival/service rate, rebalance duration, idle consumers, processing p99, and replica oscillation. Test 10x spikes and dependency slowdown separately.
## Test yourself
1. What causes autoscaling flapping?
2. Why can adding replicas temporarily reduce throughput?
3. Which signal distinguishes spike from slow sink?
Continue to [`professional.md`](professional.md).
