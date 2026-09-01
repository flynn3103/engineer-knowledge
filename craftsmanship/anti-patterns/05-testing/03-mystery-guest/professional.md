# Mystery Guest — Professional

> **Focus:** tests that rely on hidden files, databases, environment values, or shared setup.

## What this guide builds

At the professional level, learn to **make prevention a repeatable team practice**. The goal is not perfect code; it is to make the next decision clearer and safer.

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

- Set a shared rule, automate a useful signal, review trends, and adjust the practice from results.
- Write down the behavior or constraint that must not change.
- Prefer a small, reversible step over a broad rewrite.
- Verify the result with the fastest relevant test, check, or measurement.

## Evidence of progress

An operating practice that reduces recurrence without blocking delivery.

## Check yourself

- What observable signal tells you this anti-pattern is present?
- What is the smallest change that reduces the risk?
- How will you know the improvement preserved the required behavior?
