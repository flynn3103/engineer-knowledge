# Diagnostics — Professional

OpenTelemetry standardizes traces, metrics, logs, context propagation, and semantic conventions, but collectors and backends still require capacity and tenancy design. Prometheus’s label model makes dimensional queries powerful while high-cardinality labels multiply time series. Linux eBPF enables low-overhead kernel and user-space observation but adds verifier, privilege, and symbolization constraints. Parca and Pyroscope use profile aggregation to make continuous profiling operationally affordable.

At 10× scale, cardinality and ingestion cost dominate. At 100×, tail-sampling buffers, collector backpressure, tenant isolation, retention, and query latency become architecture. Dashboard dropped telemetry, collector queue depth, ingestion bytes, active series, trace completeness, profile coverage, and cost per service.

## Design and operations checklist

1. Begin with operational questions and SLOs.
2. Standardize context and semantic fields.
3. Bound cardinality, payload, retention, and access.
4. Preserve enough healthy traffic for comparison.
5. Test collector and backend failure behavior.
6. Separate audit, diagnostic, and product analytics data.
7. Make incident learning change telemetry or runbooks.

```text
QUESTION -> SIGNAL -> CONTEXT -> PIPELINE -> STORAGE -> QUERY -> DECISION
          quality + cost + privacy + resilience + ownership
```

## Test yourself

1. Design telemetry for a 10,000-service platform without unbounded cardinality.
2. How does tail sampling fail when collectors are saturated?
3. Which eBPF access controls are required in a multi-tenant cluster?
4. How would you prove continuous profiling pays for itself?

## Further reading

- OpenTelemetry specifications and semantic conventions.
- Prometheus documentation on data models and cardinality.
- Brendan Gregg, *Systems Performance* and BPF Performance Tools.
- Google SRE books on monitoring distributed systems.
