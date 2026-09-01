# Chaos Engineering — Professional

Netflix Chaos Monkey terminates instances; Chaos Mesh and Litmus use Kubernetes custom resources for faults; AWS Fault Injection Service integrates cloud targets and stop conditions. At scale, experiment control-plane security, overlapping faults, and organizational coordination dominate.

## Design and operations checklist

1. Derive experiments from risk and incidents.
2. Define measurable steady state and aborts.
3. Bound scope, credentials, and concurrency.
4. Validate cleanup and recovery.
5. Track findings to durable controls.

```text
RISK -> HYPOTHESIS -> SAFE FAULT -> OBSERVE -> ABORT/RECOVER -> IMPROVE
```

## Test yourself

1. Design chaos governance for a shared cluster.
2. How can the experiment platform cause an outage?
3. Which production-only evidence justifies risk?
4. How do you measure resilience improvement?

## Further reading

- Principles of Chaos Engineering.
- Casey Rosenthal and Nora Jones, *Chaos Engineering*.
- Netflix and AWS fault-injection documentation.
