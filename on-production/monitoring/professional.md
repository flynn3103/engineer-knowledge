# Monitoring — Professional

Prometheus evaluates label-based time series and recording rules; Alertmanager groups and routes notifications; Grafana visualizes multiple sources; black-box probes test externally visible paths. At scale, cardinality, rule evaluation, federation, tenant isolation, and alert ownership dominate.

## Design and operations checklist

1. Monitor user outcomes and critical invariants.
2. Bound cardinality and retention.
3. Make alert routes and ownership testable.
4. Design monitoring as a resilient dependency.
5. Audit noise, misses, and operator load.
6. Preserve privacy in usage and security signals.

```text
USER OUTCOME -> SIGNAL -> RULE -> ROUTE -> ACTION -> LEARNING
```

## Test yourself

1. Design monitoring for a multi-region fleet.
2. How does high cardinality become an outage?
3. Which alerts should automate mitigation?
4. How do you measure alert quality?

## Further reading

- Google SRE, Monitoring Distributed Systems.
- Prometheus and Alertmanager documentation.
- Rob Ewaschuk, “My Philosophy on Alerting.”
