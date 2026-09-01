# Distributed Tracing — Senior

<!-- level-focus -->
At senior level, design tracing for partial failure, sampling, and evolving service topology.

## Set tracing invariants

Require propagation at ingress and egress, bounded attributes, and a safe fallback when exporters fail. Tail-sample errors and slow paths so rare evidence survives; publish sampling decisions and dropped-span metrics. In a fan-out request, distinguish parallel child spans from serial work before blaming the widest visual branch.

## Apply it

1. Model fan-out and an async boundary.
2. Test a failed exporter and a sampled error trace.
3. Record privacy and retention rules for attributes.

## Verify your work

- Export failure does not delay requests.
- Error traces are findable despite normal sampling.

## Review questions

- What causes a trace tree to be misleading during parallel work?
- Which attributes require governance?
