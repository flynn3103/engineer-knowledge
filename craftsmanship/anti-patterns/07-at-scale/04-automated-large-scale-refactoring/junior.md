# Automated Large-Scale Refactoring — Junior

> **Focus:** repetitive edits performed manually or automated edits shipped without safeguards.

## What this guide builds

At the junior level, learn to **recognize the pattern in a small change**. The goal is not perfect code; it is to make the next decision clearer and safer.

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
