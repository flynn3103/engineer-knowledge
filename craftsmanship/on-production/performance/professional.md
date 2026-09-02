# Performance — Professional

Linux `perf` samples hardware and kernel events; eBPF observes scheduling and I/O; JVM Flight Recorder captures runtime events with low overhead; continuous profilers aggregate stack samples across fleets. At 10× load, queueing and pools dominate; at 100×, memory locality, data movement, and fleet economics become architectural.

## Design and operations checklist

1. Define user-visible budgets and representative workloads.
2. Correlate latency with saturation and profiles.
3. Preserve benchmark reproducibility and variance.
4. Test failure and recovery load.
5. Gate meaningful regressions and review false positives.
6. Track cost per useful operation.

```text
WORKLOAD -> QUEUES -> RESOURCES -> PROFILE -> CHANGE -> REGRESSION GUARD
```

## Test yourself

1. Design performance governance for a polyglot fleet.
2. How does coordinated omission corrupt load results?
3. Which hardware counters explain cache-bound code?
4. When is a performance regression acceptable?

## Further reading

- Brendan Gregg, *Systems Performance*.
- Gil Tene on latency and coordinated omission.
- Neil Gunther, *Guerrilla Capacity Planning*.
