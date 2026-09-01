# Diagnostics — Middle

Instrument boundaries with operation, outcome, duration, and correlation. Use RED metrics—rate, errors, duration—for services and USE—utilization, saturation, errors—for resources.

Propagate trace context through HTTP, queues, and background jobs. Use structured logs that can join on trace, request, tenant, and deployment identifiers without unbounded-cardinality fields.

Profiles answer CPU, allocation, lock, and I/O questions. Continuous profiling reveals regressions that one-off local profiling misses. Diagnostic endpoints should expose safe, authenticated state—not secrets or an unbounded dump.

Sampling is a fidelity decision: head sampling controls cost early; tail sampling can retain slow or failed traces after outcome is known. Document what the sample cannot prove.

## Test yourself

1. Which RED and USE metrics fit a queue worker?
2. How does trace context cross an asynchronous boundary?
3. What cardinality mistake can break a metrics backend?
4. When is tail sampling worth its cost?

Continue to [`senior.md`](senior.md).
