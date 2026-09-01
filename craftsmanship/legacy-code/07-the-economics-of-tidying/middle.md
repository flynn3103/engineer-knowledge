# The Economics of Tidying — Middle

Compare a tidy’s cost now with its expected future savings. Future savings are uncertain, so favor work that pays back on the next few known changes.

## A lightweight calculation

```text
expected value = (saving per future change × likely number of changes) - tidy cost
```

Example: a 30-minute extraction is expected to save 15 minutes on each of four committed changes. Estimated value: `15 × 4 - 30 = 30` minutes. The estimate need not be perfect; it only needs to expose assumptions.

## Factors that change the answer

- **Coupling:** a tidy that reduces the number of files affected can save repeatedly.
- **Cohesion:** putting related rules together lowers search and reasoning time.
- **Timing:** near-term work is more certain and valuable than a vague future plan.
- **Risk:** a cleanup that prevents a likely production error has value beyond typing time.
- **Reversibility:** small changes have low recovery cost.

## Practical use

Tie tidying to a concrete backlog item or current task. Estimate in rough ranges, set a time limit, and stop if the work uncovers a redesign. Do not manufacture precise spreadsheets from weak guesses.
