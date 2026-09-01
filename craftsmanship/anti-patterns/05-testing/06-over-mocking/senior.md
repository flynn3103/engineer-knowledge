# Over-Mocking — Senior

> **Focus:** tests that verify implementation choreography rather than behavior.

## What this guide builds

At the senior level, learn to **contain risk across a changing system boundary**. The goal is not perfect code; it is to make the next decision clearer and safer.

## Recognize the pattern

A refactor changes internal calls and breaks tests without changing the result.

Common signals:

- The intent is hard to infer from the call site or module boundary.
- A small change creates surprising work, delay, or risk elsewhere.
- The code needs an undocumented rule to stay correct.

## A better direction

Use real collaborators when they are cheap; fake only expensive or external boundaries.

## Python example

```python
def test_receipt_is_saved():
    repository = InMemoryReceipts()
    service = CheckoutService(repository)
    service.checkout(cart_with_total(25))
    assert repository.all()[0].total == 25
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
