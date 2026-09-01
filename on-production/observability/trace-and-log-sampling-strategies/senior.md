# Trace and Log Sampling Strategies — Senior

<!-- level-focus -->
At senior level, design adaptive sampling under incidents, cost pressure, and privacy constraints.

## Method

Prefer tail sampling when final status or latency determines value. Bound buffers, expose dropped decisions, and test collector overload. Use redaction before storage; sampling is not a privacy control.

## Apply it

1. Define tail policies for error and latency.
2. Simulate overload.

## Verify your work

- Overload does not affect serving traffic.
- Lost evidence is measurable.

## Review questions

- What information does tail sampling need that head sampling lacks?
