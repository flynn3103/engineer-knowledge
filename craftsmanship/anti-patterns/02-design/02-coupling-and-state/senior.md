# Coupling & State Anti-Patterns — Senior

> **Focus:** hidden dependencies, temporal coupling, and state that leaks across boundaries.

## What this guide builds

At the senior level, learn to **contain risk across a changing system boundary**. The goal is not perfect code; it is to make the next decision clearer and safer.

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

- Map impact, stage the change, define rollback or containment, and validate the important assumptions.
- Write down the behavior or constraint that must not change.
- Prefer a small, reversible step over a broad rewrite.
- Verify the result with the fastest relevant test, check, or measurement.

## Evidence of progress

A migration or improvement plan with measurable guardrails.

## Check yourself

- What observable signal tells you this anti-pattern is present?
- What is the smallest change that reduces the risk?
- How will you know the improvement preserved the required behavior?
