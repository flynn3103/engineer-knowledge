# Coupling & State Anti-Patterns — Junior

> **Focus:** hidden dependencies, temporal coupling, and state that leaks across boundaries.

## What this guide builds

At the junior level, learn to **recognize the pattern in a small change**. The goal is not perfect code; it is to make the next decision clearer and safer.

## Recognize the pattern

A change in one component unexpectedly forces changes or ordering in another.

Common signals:

- The intent is hard to infer from the call site or module boundary.
- A small change creates surprising work, delay, or risk elsewhere.
- The code needs an undocumented rule to stay correct.

## A better direction

Make dependencies explicit, narrow the interface, and keep mutable state owned by one place.

## Python example

```python
class ReportService:
    def __init__(self, clock):
        self.clock = clock  # explicit dependency

    def build(self, report):
        return {"created_at": self.clock.now(), "report": report}
```

## Action checklist

- Name the smell, find the smallest affected boundary, and make one safe improvement.
- Write down the behavior or constraint that must not change.
- Prefer a small, reversible step over a broad rewrite.
- Verify the result with the fastest relevant test, check, or measurement.

## Evidence of progress

A short before/after note and a focused test or check.

## Check yourself

- What observable signal tells you this anti-pattern is present?
- What is the smallest change that reduces the risk?
- How will you know the improvement preserved the required behavior?
