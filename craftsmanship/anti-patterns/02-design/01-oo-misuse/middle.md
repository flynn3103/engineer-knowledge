# OO Misuse Anti-Patterns — Middle

> **Focus:** objects used as data bags, procedure holders, or inheritance shortcuts.

## What this guide builds

At the middle level, learn to **diagnose and repair the pattern in a component**. The goal is not perfect code; it is to make the next decision clearer and safer.

## Recognize the pattern

Objects expose raw data while rules live elsewhere; helper base classes and flags hide intent.

Common signals:

- The intent is hard to infer from the call site or module boundary.
- A small change creates surprising work, delay, or risk elsewhere.
- The code needs an undocumented rule to stay correct.

## A better direction

Put behavior with the data, use composition for reuse, and give each operation a clear name.

## Python example

```python
class Account:
    def __init__(self, balance: int):
        self.balance = balance

# Bad: callers change account.balance directly
# Better: account.withdraw(amount) protects the rule.
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
