# Trace and Log Sampling Strategies — Junior

<!-- level-focus -->
At junior level, select a simple sampling rule while retaining useful failures.

## Method

Sampling keeps a subset of high-volume telemetry. Start with all errors and a small random share of successful requests. Record the sample decision so query results are not mistaken for complete traffic.

## Apply it

1. Configure error retention and a success rate.
2. Generate successes and failures.

## Verify your work

- Failed requests remain searchable.
- Sample rate is visible.

## Review questions

- Why sample successful traffic differently from errors?
