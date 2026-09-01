# Cardinality and Metrics Cost — Senior

<!-- level-focus -->
At senior level, enforce cardinality limits across tenants without hiding an incident.

## Method

Monitor active series, reject or relabel unsafe data at ingestion, and preserve high-detail investigation in sampled traces and logs. Test a runaway label and confirm service availability survives.

## Apply it

1. Define tenant limits.
2. Drill a cardinality spike.

## Verify your work

- Rejection is visible to the producer.

## Review questions

- Why should limits exist before storage?
