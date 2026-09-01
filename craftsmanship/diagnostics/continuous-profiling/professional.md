# Continuous Profiling — Professional

> Use low-overhead production profiles to locate CPU, allocation, and blocking regressions over time.

## Goal

- Establish a repeatable, measurable standard across teams.

## Key ideas

- Use low-overhead production profiles to locate CPU, allocation, and blocking regressions over time.
- Prefer evidence and small, reversible steps over assumptions.
- Make the operational impact visible to the people who support the system.

## Action checklist

- Start with the user-facing or operational question.
- Make one bounded change and verify its outcome.
- Document the decision, ownership, and rollback path.

## Avoid

- Adding detail or tooling without a question it must answer.
- Treating a deployment as proof that the operational path works.

## Practice

- Apply this topic to one real service, including its failure path.

## Review questions

- What evidence would show that this practice works?
- What is the smallest safe next step for this topic?
