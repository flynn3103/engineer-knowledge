# Log Aggregation — Middle

<!-- level-focus -->
At middle level, choose schemas, parsing boundaries, and retention for a multi-service flow.

## Method

Standardize required fields at the producer, not with fragile downstream parsing. Partition searches by service and time, mask sensitive fields before export, and test a deployment that changes a log schema.

## Apply it

1. Define a shared event schema.
2. Add a query for checkout failures.
3. Test malformed input handling.

## Verify your work

- Schema changes are detectable.
- Search remains useful across services.

## Review questions

- Why should producers own schema quality?
- What is the cost of parsing free text downstream?
