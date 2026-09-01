# Trace and Log Sampling Strategies — Middle

<!-- level-focus -->
At middle level, choose sampling boundaries that preserve diagnosis across a real request flow.

## Method

Use consistent trace decisions across callers and callees. Raise retention for slow routes or new releases, then lower it after evidence is sufficient. Keep audit and security events according to their separate policy.

## Apply it

1. Trace a sampled cross-service request.
2. Compare normal and slow-route retention.

## Verify your work

- Related spans are retained together.

## Review questions

- Why is independent per-service sampling misleading?
