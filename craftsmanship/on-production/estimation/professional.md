# Estimation — Professional

AWS Auto Scaling target tracking, Kubernetes HPA, and Kafka partition planning automate different control loops but cannot invent correct workload models. At 10× scale, quota, connection, and data movement limits appear; at 100×, regional capacity, fleet rollout, and supplier lead time dominate.

## Design and operations checklist

1. Connect business demand to workload units.
2. Calibrate with production distributions and benchmarks.
3. Model failure, recovery backlog, and headroom.
4. Include cost, quotas, and provisioning lead time.
5. Review forecast error and update coefficients.

```text
DEMAND -> WORKLOAD -> RESOURCE MODEL -> FAILURE SCENARIOS -> CAPACITY -> COST
```

## Test yourself

1. Design capacity planning for a seasonal global service.
2. How does autoscaling fail when the signal is delayed?
3. Which forecast errors should change architecture?
4. How do you validate recovery capacity?

## Further reading

- Neil Gunther, *Guerrilla Capacity Planning*.
- Google SRE, capacity planning and overload chapters.
- Brendan Gregg, *Systems Performance*.
