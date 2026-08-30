# OpenTelemetry — Junior

<!-- level-focus -->
At junior level, instrument one service with a vendor-neutral telemetry SDK.

## Method

OpenTelemetry creates traces, metrics, and logs through common APIs, then exports them through a collector. Add automatic HTTP instrumentation, configure an OTLP exporter, and confirm a request has a trace.

## Apply it

1. Instrument one HTTP route.
2. Export to a collector.

## Verify your work

- A request creates a named span.
- Export failure does not fail the route.

## Review questions

- What does an SDK produce?
- Why use a collector?
