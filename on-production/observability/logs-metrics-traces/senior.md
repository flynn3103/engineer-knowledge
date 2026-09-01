# Logs, Metrics, Traces — Senior

<!-- level-focus -->
At senior level, design telemetry boundaries and retention so investigation remains reliable as services and traffic change.

## Protect useful evidence

Telemetry has competing constraints: metrics need bounded labels, logs need privacy controls, and traces need sampling that retains failures. Define an event schema owned by the platform team and allow service teams to add documented fields. Require trace propagation at ingress, queues, and asynchronous workers; otherwise a trace tree silently breaks at the boundary that matters most.

For a multi-region checkout system, keep aggregate SLO metrics long enough to compare releases, retain error logs according to data policy, and tail-sample traces that are slow, failed, or explicitly requested by support. Head sampling alone can discard the rare failure after the decision was already made.

## Failure analysis

If traces disappear during a collector outage, request handling must continue: telemetry is best-effort and bounded by timeouts. Buffer only within a fixed memory/disk budget, expose dropped-telemetry metrics, and alert on the collector pipeline rather than blocking customer traffic. Test the failure by disabling the collector and verifying application latency does not rise.

## Apply it

1. Publish a schema for request logs, metrics labels, and trace attributes.
2. Choose retention and sampling rules from investigation and privacy requirements.
3. Inject a collector failure and an asynchronous handoff failure.
4. Record which evidence is intentionally lost and how an investigator detects that loss.

## Verify your work

- Trace context survives HTTP and queued work.
- Cardinality and telemetry-drop dashboards remain within agreed budgets.
- A failed request is retained by the sampling policy and can be correlated safely.

## Review questions

- What invariant prevents observability collection from becoming an availability dependency?
- When does tail sampling provide evidence that head sampling cannot?
