# Log Aggregation — Senior

<!-- level-focus -->
At senior level, design log aggregation for load spikes, privacy, and forensic reliability.

## Method

Bound buffering and ingestion rate so a collector outage cannot exhaust nodes. Define retention by data class, audit privileged queries, and expose dropped-log counters. Test an ingestion outage and prove application latency stays independent.

## Apply it

1. Set volume and retention budgets.
2. Simulate collector failure.
3. Review access to sensitive events.

## Verify your work

- Loss is visible and bounded.
- Access and retention meet policy.

## Review questions

- Why must log buffering be bounded?
- What evidence proves a privacy control works?
