# OpenTelemetry — Middle

<!-- level-focus -->
At middle level, apply semantic conventions and propagation consistently across services.

## Method

Use standard service and HTTP attributes, propagate context automatically, and add custom spans only around meaningful work. Version instrumentation as a dependency and integration-test cross-service traces.

## Apply it

1. Instrument a caller and callee.
2. Compare automatic and custom spans.

## Verify your work

- Context crosses the boundary.
- Attributes do not contain secrets.

## Review questions

- Why are semantic conventions useful?
- Which work deserves a custom span?
