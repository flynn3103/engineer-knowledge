# Async Misuse Anti-Patterns — Senior

> **Focus:** using asynchronous APIs without lifecycle, cancellation, or backpressure discipline.

## What this guide builds

At the senior level, learn to **contain risk across a changing system boundary**. The goal is not perfect code; it is to make the next decision clearer and safer.

## Recognize the pattern

A task outlives its request, blocks the loop, or overwhelms a dependency.

Common signals:

- The intent is hard to infer from the call site or module boundary.
- A small change creates surprising work, delay, or risk elsewhere.
- The code needs an undocumented rule to stay correct.

## A better direction

Keep blocking work off the event loop and make task ownership and cancellation explicit.

## Python example

```python
import asyncio

async def handle(request):
    try:
        return await do_work(request)
    except asyncio.CancelledError:
        await release_resources(request)
        raise
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
