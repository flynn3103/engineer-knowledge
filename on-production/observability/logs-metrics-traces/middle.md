# Logs, Metrics, Traces — Middle

<!-- level-focus -->
At middle level, decide how telemetry crosses the boundaries of a maintainable service rather than adding three unrelated dashboards.

## Design the correlation contract

An order flow may cross an API, worker, database, and payment provider. Give every request a propagated trace context; put the trace ID in structured logs; and use the same stable dimensions on request metrics: service, route, outcome, and region. Do not put order ID, user ID, or trace ID on a metric label: each new value creates another time series.

| Need | Signal | Stable boundary |
|---|---|---|
| Is the flow regressing? | metric | route and outcome |
| Which hop is slow? | trace | span parent/child relation |
| Why did this order fail? | log | trace ID and event name |

Add this incrementally: instrument one entry route, propagate context to one dependency, then make a saved investigation link from the metric panel to traces and logs. A dashboard without that path is harder to use under pressure.

## Scenario: checkout retries

`checkout-api` retries a timed-out payment once. Record a retry counter with `reason="timeout"`, create a child span for each attempt, and log the provider response with the trace ID. A high retry metric identifies the incident; two sibling spans show whether the retry helped; logs show the provider code. Treat the final result, not every attempt, as the customer-facing error rate.

## Apply it

1. Draw one request path and name its entry point and dependencies.
2. Specify the fields every log event must carry: timestamp, severity, service, event, and trace ID.
3. Add low-cardinality request metrics and one trace span per dependency.
4. Test a success, timeout, and retry; follow each from metric to trace to log.

## Verify your work

- A trace ID found in a gateway log finds child-service logs.
- The same request produces no unbounded metric labels.
- A teammate can start with an error-rate panel and reach evidence for one failure in minutes.

## Review questions

- Why is a trace ID suitable for a log field but not a metric label?
- Which signal should show a retry's timing and which should show its aggregate rate?
