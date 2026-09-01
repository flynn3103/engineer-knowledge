# Premature Abstraction at Scale — Middle

> **Focus:** a shared platform or common layer is created before stable common needs exist.

## What this guide builds

At the middle level, learn to **diagnose and repair the pattern in a component**. The goal is not perfect code; it is to make the next decision clearer and safer.

## Recognize the pattern

Teams inherit a rigid dependency and work around it with exceptions.

Common signals:

- The intent is hard to infer from the call site or module boundary.
- A small change creates surprising work, delay, or risk elsewhere.
- The code needs an undocumented rule to stay correct.

## A better direction

Keep local solutions local until repeated, compatible needs justify a shared contract.

## Python example

```python
def team_a_format(order):
    return {"id": order.id, "total": order.total}

# Share this only after multiple teams need the same stable contract.
```

## Action checklist

- Trace callers and dependencies, choose an explicit trade-off, and explain the local design.
- Write down the behavior or constraint that must not change.
- Prefer a small, reversible step over a broad rewrite.
- Verify the result with the fastest relevant test, check, or measurement.

## Evidence of progress

A component-level change with evidence that behavior still holds.

## Check yourself

- What observable signal tells you this anti-pattern is present?
- What is the smallest change that reduces the risk?
- How will you know the improvement preserved the required behavior?
