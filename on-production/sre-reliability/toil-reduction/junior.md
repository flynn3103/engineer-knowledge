# Toil Reduction — Junior

<!-- level-focus -->
At junior level, focus on this question:

> Can you identify repetitive operational work and safely automate one small step without hiding failures?

---

## What counts as toil

**Toil** is manual, repetitive, reactive work with little enduring value that scales with service growth. Resetting the same stuck job, copying an alert into a spreadsheet, or repeatedly resizing a known queue are common examples. Investigation, design, and one-time migration work are not automatically toil.

## Choose a candidate

Score a task with four questions: Does it repeat? Is it rule-based? Does it interrupt planned work? Does demand grow with users or machines? Start with a task that is frequent, bounded, and reversible.

## Example: safe job retry

Operators manually retry failed image jobs after a temporary storage outage. Before writing automation, establish that retries are idempotent, cap attempts at three, record each attempt, and surface failures after the cap. An automatic loop that retries a non-idempotent charge can create worse harm than the toil it removes.

## Method

1. Record frequency, duration, trigger, and current human decision.
2. Write the preconditions and stopping conditions.
3. Automate a dry-run or one narrow action first.
4. Log inputs, result, and a route for exceptions.
5. Measure whether manual interventions actually decline.

## Common mistakes

- Automating an unclear decision instead of improving its signal.
- Omitting rate limits, timeouts, or a kill switch.
- Calling a dashboard a solution when humans still act on every alert.
- Measuring script runs instead of avoided operator time.

## Apply it

1. Choose one recurring operational task.
2. Write its trigger, preconditions, maximum action count, and stop condition.
3. Design a dry-run output showing exactly what would change.

## Verify your work

- A failed automation attempt is visible and does not loop forever.
- A human can disable it quickly.
- You can compare manual time before and after rollout.

## Review questions

- Which properties separate toil from valuable engineering work?
- Why does idempotency matter for remediation automation?
- What evidence shows an automation reduced toil?
