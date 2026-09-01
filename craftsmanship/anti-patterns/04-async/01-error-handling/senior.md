# Async Error-Handling Anti-Patterns — Senior

> **Focus:** lost exceptions, unobserved failures, and error paths with no owner.

## What this guide builds

At the senior level, learn to **contain risk across a changing system boundary**. The goal is not perfect code; it is to make the next decision clearer and safer.

## Recognize the pattern

Work fails in the background and callers continue as if it succeeded.

Common signals:

- The intent is hard to infer from the call site or module boundary.
- A small change creates surprising work, delay, or risk elsewhere.
- The code needs an undocumented rule to stay correct.

## A better direction

Await or supervise every task, add context to errors, and decide how failure reaches the caller.

## Python example

```python
import asyncio

async def load_profile(client, user_id):
    try:
        return await client.get(user_id)
    except TimeoutError as exc:
        raise RuntimeError(f"profile timed out: {user_id}") from exc
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
