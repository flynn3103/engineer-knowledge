# Observability — Professional

OpenTelemetry Collector pipelines use receivers, processors, exporters, and connectors; Prometheus uses pull-based time series; Jaeger and Tempo store trace data with different indexing trade-offs; Elasticsearch/OpenSearch log clusters face shard and mapping pressure. At 100×, schema governance, cardinality, tail buffers, query isolation, and cost allocation dominate.

## Design and operations checklist

1. Start from SLIs and diagnostic questions.
2. Standardize context and semantic contracts.
3. Bound cardinality, sampling, and retention.
4. Isolate tenants and sensitive data.
5. Monitor telemetry loss and query health.
6. Fund instrumentation as product capability.

```text
CODE -> TELEMETRY CONTRACT -> COLLECTOR -> STORAGE -> QUERY -> DECISION
```

## Test yourself

1. Design a multi-tenant OpenTelemetry pipeline.
2. How do schema changes break fleet queries?
3. Which sampling strategy preserves SLO investigations?
4. How do you attribute telemetry cost fairly?

## Further reading

- OpenTelemetry specifications.
- Charity Majors et al., *Observability Engineering*.
- Google SRE books on SLIs and SLOs.
