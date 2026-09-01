# Shared State Anti-Patterns — Senior

> **Focus:** mutable state shared by concurrent work without a single owner.

## What this guide builds

At the senior level, learn to **contain risk across a changing system boundary**. The goal is not perfect code; it is to make the next decision clearer and safer.

## Recognize the pattern

Two operations depend on timing and produce different results across runs.

Common signals:

- The intent is hard to infer from the call site or module boundary.
- A small change creates surprising work, delay, or risk elsewhere.
- The code needs an undocumented rule to stay correct.

## A better direction

Prefer message passing or immutable values; if mutation is needed, give it one owner.

## Python example

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Job:
    user_id: str
    attempt: int

# Pass a new Job instead of mutating a shared dictionary.
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
