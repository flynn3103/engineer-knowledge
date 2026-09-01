# Mystery Guest — Middle

> **Focus:** tests that rely on hidden files, databases, environment values, or shared setup.

## What this guide builds

At the middle level, learn to **diagnose and repair the pattern in a component**. The goal is not perfect code; it is to make the next decision clearer and safer.

## Recognize the pattern

A reader cannot see what data makes the test pass.

Common signals:

- The intent is hard to infer from the call site or module boundary.
- A small change creates surprising work, delay, or risk elsewhere.
- The code needs an undocumented rule to stay correct.

## A better direction

Create required data in the test or a clearly named fixture; keep dependencies visible.

## Python example

```python
def test_sends_welcome_email():
    mailbox = FakeMailbox()
    service = SignupService(mailbox)
    service.signup("sam@example.com")
    assert mailbox.sent_to == ["sam@example.com"]
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
