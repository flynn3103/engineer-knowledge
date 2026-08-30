# Metrics Pipelines — Middle

<!-- level-focus -->
At middle level, choose collection boundaries and labels that keep a growing service queryable.

## Build a reliable path

Use service discovery rather than static targets when instances change. Relabel only stable metadata, authenticate scrape endpoints, and give recording rules names that downstream dashboards can depend on. For short jobs, push completion data deliberately and delete it when its lifecycle ends.

## Apply it

1. Replace one static target with discovery.
2. Add a recording rule for an error ratio.
3. Simulate a disappearing target and inspect `up`.

## Verify your work

- Target churn does not leave stale series or silent gaps.
- A dashboard uses a tested recording rule.

## Review questions

- Why does discovery reduce operational change cost?
- When is a Pushgateway lifecycle a risk?
