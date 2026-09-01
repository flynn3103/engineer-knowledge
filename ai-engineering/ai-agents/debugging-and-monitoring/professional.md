# Debugging and Monitoring - Professional

Agent observability is a high-cardinality distributed tracing problem with
unusually sensitive payloads and a weak relationship between transport
success and semantic success.

## Real-system mechanics

**OpenTelemetry** propagates trace context and exports spans through SDKs and
collectors. Tail sampling can retain errors and slow traces after seeing the
whole trace, unlike head sampling, but requires buffering and consistent trace
routing in the collector tier.

**Langfuse** and **LangSmith** link LLM generations, traces, datasets, and
feedback. Their product models help investigation, but teams still own data
classification, regional storage, access control, sampling, and retention.

**Prometheus** stores dimensional time series efficiently only when labels are
bounded. Put model/tool/version/error class in labels; put run IDs and raw
arguments in traces or logs. Histograms support latency distributions without
one series per request.

## Scale and failure behavior

At 10x, raw content and streaming token events dominate telemetry volume. At
100x, collector queues, span cardinality, and vendor ingestion quotas can fail
the observability system during the incident when it is most needed. Use
bounded queues, memory limiters, disk buffering where justified, and explicit
drop counters.

Telemetry must never block the request path indefinitely. Prefer losing a
sampled success trace to causing an outage, but preserve aggregate counters
and high-severity events through independent paths. Tail sampling policies
should retain policy denials, errors, high latency, and a representative
baseline.

## Operations

Dashboard ingest lag, dropped spans/logs, collector memory/queue utilization,
sampling rates, redaction failures, metric series count, trace completeness,
and telemetry cost alongside agent SLOs. A telemetry schema change requires a
compatibility and cardinality review.

Postmortems should reconstruct causal transitions from durable execution data
and traces. If the trace is incomplete, identify whether propagation,
sampling, export, or retention removed the evidence.

## Design and operations checklist

- [ ] Trace context survives HTTP, queues, workers, and tool calls.
- [ ] Metric labels are bounded and reviewed for cardinality.
- [ ] Sensitive content is minimized and redacted before export.
- [ ] Sampling preserves errors, safety events, slow traces, and a baseline.
- [ ] Telemetry backpressure cannot take down serving.
- [ ] Collector health and dropped-data counters are monitored.

## Cheat sheet

```text
metric = bounded aggregate for alerting
trace  = causal path for one run
log    = detailed event evidence
head sampling = decide before trace completes
tail sampling = decide after observing outcome
semantic success != HTTP success
```

## Test yourself

1. Design a tail-sampling policy for a million runs per hour.
2. Why can one `user_id` metric label destabilize Prometheus?
3. How should serving behave when every telemetry collector is unavailable?

## Further reading

- OpenTelemetry specifications and Collector documentation
- Prometheus documentation, "Instrumentation" and histogram practices
- Google SRE Workbook, "Alerting on SLOs"
- Langfuse and LangSmith tracing/documentation repositories
- NIST guidance on log management and privacy engineering
