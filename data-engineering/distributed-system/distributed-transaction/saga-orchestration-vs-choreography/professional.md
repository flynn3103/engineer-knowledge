# Saga: Orchestration vs Choreography - Professional

A Saga is a durable state machine whose correctness depends on business invariants, not global isolation.

## Real systems

- Temporal persists workflow histories and deterministically replays workflow code.
- AWS Step Functions stores orchestration state and retry/catch policy.
- Camunda models BPMN compensation and incidents.
- Kafka-based choreography relies on log retention, keys, and consumer idempotency rather than a central state machine.

At scale, history growth, retry storms, hot correlation keys, and version skew dominate. Dashboard state age, transition latency, compensation success, history size, and replay failures.

## Design and operations checklist

- State business invariants and compensability per step.
- Persist transitions and messages atomically.
- Version workflows for executions spanning deployments.
- Provide search, pause, retry, and repair controls.

```text
forward action: local commit
compensation: explicit semantic repair
```

## Test yourself

1. How do you change workflow code while histories are active?
2. Which invariant cannot be restored by compensation?
3. What evidence favors choreography over orchestration?

## Further reading

- Garcia-Molina and Salem, *Sagas*.
- Temporal durable execution documentation.
- Richardson, *Microservices Patterns*.
