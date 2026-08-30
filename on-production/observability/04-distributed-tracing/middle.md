# Distributed Tracing — Middle

<!-- level-focus -->
At middle level, propagate trace context through maintainable service and asynchronous boundaries.

## Preserve the request story

Use framework middleware to create server spans and client instrumentation to inject context automatically. For a queue, carry trace context in message headers and create a consumer span that links to the producer span. Name spans by stable operations, not IDs, and record errors without credentials or personal data.

## Apply it

1. Trace an HTTP call and one queued job.
2. Add a timeout and confirm the failing span has status and cause.
3. Compare a trace before and after a retry.

## Verify your work

- Parent-child relationships survive every boundary.
- Span names aggregate useful operations.

## Review questions

- Why should span names avoid request identifiers?
- How does queued work retain causality?
