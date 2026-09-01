# Automated Large-Scale Refactoring — Middle

> **Focus:** repetitive edits performed manually or automated edits shipped without safeguards.

## What this guide builds

At the middle level, learn to **diagnose and repair the pattern in a component**. The goal is not perfect code; it is to make the next decision clearer and safer.

## Recognize the pattern

The change is inconsistent, too costly to review, or silently changes behavior.

Common signals:

- The intent is hard to infer from the call site or module boundary.
- A small change creates surprising work, delay, or risk elsewhere.
- The code needs an undocumented rule to stay correct.

## A better direction

Specify the transformation, run it in small batches, and validate every batch.

## Python example

```python
def rename_call(source: str) -> str:
    return source.replace("old_api(", "new_api(")

# Pair automated changes with targeted tests and review.
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
