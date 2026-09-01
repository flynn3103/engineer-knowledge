# OpenTelemetry — Senior

<!-- level-focus -->
At senior level, design collector pipelines, sampling, and attribute governance for scale.

## Method

Use collectors for batching, retry, filtering, and routing. Bound queues, redact before export, monitor drops, and test backend loss. Maintain compatibility when teams upgrade SDKs.

## Apply it

1. Define processor order.
2. Test collector backpressure.

## Verify your work

- Application latency remains independent.
- Drops and redaction are observable.

## Review questions

- Why is processor order significant?
- What invariant limits exporter failure?
