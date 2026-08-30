# Logs, Metrics, Traces — Professional

<!-- level-focus -->
At professional level, create an operating model in which teams can evolve telemetry without losing customer, cost, or privacy accountability.

## Make observability a product contract

Set a cross-team contract: platform owns collectors, query reliability, and schema tooling; service teams own meaningful events and runbooks; security approves redaction and retention. Deliver changes in reversible increments: publish schema linting, migrate one critical flow, measure investigation time and telemetry cost, then enforce the contract for new services.

Use outcome measures rather than dashboard count: percentage of critical flows with end-to-end context, time from page to a linked trace, sampled-error coverage, cost per million requests, and policy violations. Escalate when a team emits sensitive fields or bypasses cardinality limits; the accountable owner fixes the producer rather than the central team silently filtering evidence.

## Apply it

1. Name owners for platform reliability, service semantics, and data governance.
2. Define rollout gates for schema migration and a rollback for collector changes.
3. Review a quarterly evidence sample from an incident and a support investigation.

## Verify your work

- Ownership, retention, and escalation are documented and exercised.
- New services meet the contract before production launch.
- Investigation speed and telemetry spend improve or remain within agreed bounds.

## Review questions

- Which team should own the meaning of a business failure event?
- What evidence would justify tightening a telemetry governance rule?
