# Metrics Pipelines — Senior

<!-- level-focus -->
At senior level, design a metrics pipeline that survives scale, regional failure, and cardinality pressure.

## Protect ingestion and queries

Separate collection, durable storage, and query boundaries. Enforce label budgets at ingestion, monitor scrape and remote-write lag, and decide which aggregates are precomputed. During a regional outage, retain local evidence where possible and expose gaps rather than fabricating continuity.

## Apply it

1. Set cardinality and retention budgets.
2. Test remote-write backpressure and collector loss.
3. Identify a query that should become a recording rule.

## Verify your work

- Pipeline health has its own dashboards and alerts.
- Load loss is detectable and bounded.

## Review questions

- What evidence distinguishes a quiet service from a broken scrape?
- Why must cardinality limits be enforced before storage?
