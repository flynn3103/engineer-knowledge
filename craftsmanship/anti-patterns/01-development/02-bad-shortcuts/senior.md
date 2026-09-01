# Bad Shortcuts Anti-Patterns — Senior

> At scale, shortcuts become inconsistent contracts, leaked secrets, silent failures, and costly coordinated migrations.

## Goal

Run safe, measurable campaigns that improve shared conventions without forcing an all-at-once rewrite.

## Establish a migration map

- Inventory owners, consumers, formats, secrets, and critical error paths.
- Prioritize by customer risk and change frequency, not by the number of lint violations.
- Define a target contract, a compatibility period, and a deletion date.
- Add detection first: scanners, structured logs, metrics, and CI checks.

## Evolve contracts with parallel change

```python
def parse_status(value):
    aliases = {"in_progress": "processing", "working": "processing"}
    normalized = aliases.get(value, value)
    if normalized not in {"new", "processing", "done"}:
        raise ValueError(f"unknown status: {value}")
    return normalized
```

Accept old values for a defined window, emit a migration signal, move producers and consumers, then remove aliases. Do not leave compatibility forever.

## Campaign patterns

| Problem | Safe campaign |
|---|---|
| Duplicated policy | Name one owner; migrate callers behind a stable API. |
| Secrets in code | Rotate first, scan history and CI, then remove references. |
| Magic values | Introduce named constants or types; migrate by domain. |
| Broad error handling | Define taxonomy, instrument unknown failures, tighten catches. |
| Free-form strings | Publish a versioned contract and add boundary validation. |

## Governance that helps delivery

- Provide a small approved configuration and error-handling standard.
- Make the safe path easy: templates, libraries, examples, and automatic checks.
- Give exceptions an owner and expiration date.
- Review recurring violations as a system problem, not an individual failure.

## When a shortcut is acceptable

A local script, a one-time migration, or a time-boxed incident mitigation may justify a shortcut. State its scope, owner, risk, and removal condition before it escapes into a shared path.

## Check your understanding

1. What signal proves an old contract can be removed?
2. How would you rotate a secret without causing an outage?
3. Which shortcut needs a campaign rather than a code-review comment?
