# Bad Shortcuts Anti-Patterns — Junior

> A shortcut is harmful when it hides meaning, duplicates a future change, or turns a recoverable failure into a mystery.

## Goal

Recognize six shortcuts and choose the smallest alternative that makes intent explicit.

## The shortcuts

| Anti-pattern | Signal | Better first move |
|---|---|---|
| Copy-paste programming | The same rule appears in several places. | Extract only the stable shared rule. |
| Magic values | `7`, `"gold"`, or a URL has no explanation. | Give the domain value a name. |
| Hard coding | Environment or customer data is in source. | Inject configuration or data. |
| Cargo cult programming | A pattern is copied without knowing its purpose. | State the problem it solves. |
| Pokémon exception handling | Errors are caught broadly and ignored. | Handle expected failures precisely. |
| Stringly typed programming | Important states travel as arbitrary text. | Model valid values. |

## Give values and states meaning

```python
from enum import StrEnum

MAX_RETRY_ATTEMPTS = 3

class Plan(StrEnum):
    FREE = "free"
    PRO = "pro"

def can_retry(attempts, plan):
    return plan is Plan.PRO and attempts < MAX_RETRY_ATTEMPTS
```

The name tells readers why the value exists. A type or enum limits accidental invalid values.

## Handle only errors you expect

```python
def load_profile(client, user_id):
    try:
        return client.get_profile(user_id)
    except ProfileNotFound:
        return None
```

Do not use `except Exception: pass`. It hides defects and removes the information needed to repair them. Let unexpected errors fail visibly or add context and re-raise them.

## Copy with care

- Duplicate a few lines while the cases are still different.
- Extract shared behavior when a real rule changes together.
- Keep configuration outside source when it varies by deployment, tenant, or secret.
- Before copying a pattern, explain its precondition and failure mode in one sentence.

## Before you commit

- Can a new reader understand each value without searching?
- Would changing this business rule require editing more than one place?
- Is an error being handled, retried, reported, or deliberately propagated?
- Can invalid input enter this API as a plain string?

## Check your understanding

1. When is duplication cheaper than a shared abstraction?
2. Why is a broad swallowed exception dangerous?
3. Which literal in your current change needs a domain name?
