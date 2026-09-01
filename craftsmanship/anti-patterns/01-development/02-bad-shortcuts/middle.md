# Bad Shortcuts Anti-Patterns — Middle

> The middle-level skill is choosing boundaries that remove accidental work without creating a framework for every variation.

## Goal

Make shortcuts visible in design and review, then replace them with explicit contracts, ownership, and error flow.

## Decide whether to share

Use this test before extracting duplication:

1. Do the copies represent the same business rule?
2. Do they change together today, not merely in theory?
3. Can the extracted API be named without vague words such as `common` or `utils`?

If any answer is no, keep local duplication and revisit after more evidence.

```python
def calculate_member_shipping(weight):
    return max(0, weight * 2 - 5)

def calculate_guest_shipping(weight):
    return max(0, weight * 2 - 5)

# Extract only after both callers truly share the same policy.
def calculate_shipping(weight, discount):
    return max(0, weight * 2 - discount)
```

## Configuration has an owner

- Keep deploy-time values in validated configuration, not source code.
- Keep secrets in a secret manager or injected environment, never in defaults or logs.
- Keep business policy in code unless non-engineers genuinely need to own safe, audited changes.
- Validate configuration at startup so failures are immediate and actionable.

## Design error flow

| Failure | Response |
|---|---|
| Expected absence | Return an explicit optional result. |
| Retryable dependency fault | Retry with bounded attempts and telemetry. |
| Invalid caller input | Return or raise a clear validation error. |
| Programming defect | Preserve context and fail loudly. |

```python
def parse_quantity(value):
    try:
        quantity = int(value)
    except ValueError as error:
        raise InvalidQuantity(value) from error
    if quantity < 1:
        raise InvalidQuantity(value)
    return quantity
```

## Review questions

- What does this copied pattern rely on, and is that precondition true here?
- Who changes this configuration, and how is it validated and audited?
- Is the error classification visible to callers and monitoring?
- Can the domain type reject invalid values at the boundary?

## Check your understanding

1. What turns two copies into a shared rule?
2. Which configuration belongs in code, deployment config, or a product-owned system?
3. How would you make a stringly typed status impossible to misuse?
