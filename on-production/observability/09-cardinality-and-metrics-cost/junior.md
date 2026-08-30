# Cardinality and Metrics Cost — Junior

<!-- level-focus -->
At junior level, prevent one metric label from creating unbounded time series.

## Method

Cardinality is the number of distinct label combinations. Use `status` and `route`; never use user ID, request ID, or full URL. Put unique values in logs or traces instead.

## Apply it

1. Inspect labels on one metric.
2. Replace a unique label with a bounded category.

## Verify your work

- Series count stays stable as users grow.

## Review questions

- Why is user ID unsafe as a label?
