# Cardinality and Metrics Cost — Middle

<!-- level-focus -->
At middle level, choose labels and aggregations that preserve useful queries within a service budget.

## Method

Document allowed dimensions, aggregate dynamic paths into route templates, and use recording rules for expensive repeated queries. Review cardinality during feature design.

## Apply it

1. Budget a new metric.
2. Test a route-label change.

## Verify your work

- Dashboard queries remain fast.

## Review questions

- Which label combinations multiply series count?
