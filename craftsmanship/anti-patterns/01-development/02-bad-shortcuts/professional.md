# Bad Shortcuts Anti-Patterns — Professional

> Professional practice turns “be careful” into observable contracts, safe defaults, and feedback loops.

## Goal

Make correctness and recovery measurable across teams while avoiding policy that slows ordinary work.

## Evidence for shortcut decisions

| Claim | Evidence to collect |
|---|---|
| Duplication is expensive | Change history, defect correlation, and ownership friction. |
| A value should be configurable | Distinct deploy or customer requirements and a safe ownership path. |
| An error should retry | Error class, dependency behavior, attempt rate, and success after retry. |
| A type migration is worth it | Invalid-input rate, integration cost, and compatibility risk. |

```python
def retry(operation, attempts=3):
    for attempt in range(attempts):
        try:
            return operation()
        except TransientError:
            if attempt == attempts - 1:
                raise
```

Measure retry volume, exhaustion, and added latency. A retry without those signals is a hidden failure policy.

## Operating controls

- Enforce secret scanning, dependency review, and obvious unsafe patterns in CI.
- Publish versioned schemas and compatibility expectations for shared data.
- Set error budgets and alert on unknown error classes, not every individual exception.
- Review configuration changes for validation, auditability, rollout, and rollback.
- Prefer a few clear rules with local ownership over a universal abstraction.

## Decision record

- **Intent:** What short-term pressure caused the shortcut?
- **Contract:** What callers, data, or operators rely on it?
- **Evidence:** Which metrics, tests, or incidents matter?
- **Control:** What automated guardrail will prevent recurrence?
- **Exit:** Who removes the temporary path, and by when?

## Check your understanding

1. Which metric would show that retry behavior harms users?
2. How do you distinguish necessary configuration from soft-coded business logic?
3. What guardrail prevents a secret leak before review?
