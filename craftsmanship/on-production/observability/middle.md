# Observability — Middle

Instrument service entry, external calls, queue operations, and major domain transitions. Use OpenTelemetry semantic conventions where they fit. Build SLI queries from telemetry and test them against known requests.

Head sampling decides early and controls cost; tail sampling retains traces based on latency or error but needs buffering. Logs and traces need retention and access controls; metrics need cardinality budgets.

## Test yourself

1. Which boundaries deserve spans?
2. How does tail sampling fail under pressure?
3. What evidence validates an SLI query?
4. Where should sensitive fields be removed?

Continue to [`senior.md`](senior.md).
