# RED and USE Methods — Senior

<!-- level-focus -->
At senior level, use RED and USE as an architectural coverage model for bottlenecks and failure isolation.

## Link symptoms to constrained resources

RED measures request rate, errors, and duration at service boundaries. USE measures utilization, saturation, and errors for finite resources. For checkout, connect the API's p99 duration to its database-pool queue and database disk latency. The invariant is that every customer-facing symptom has an owned dependency path, while every scarce resource has a saturation signal before it fails.

Test a controlled pool limit or slow query. A rising queue with stable request rate indicates contention, not traffic growth. Preserve evidence through deploys by using stable service and route names.

## Apply it

1. Map critical request paths and scarce resources.
2. Link each RED panel to its relevant USE panels.
3. Inject one safe saturation condition and write the recovery threshold.

## Verify your work

- On-call can distinguish demand growth from resource contention.
- A resource alert identifies an owner and affected services.

## Review questions

- Why can CPU utilization alone miss a saturation problem?
- Which resource signals should precede a latency page?
