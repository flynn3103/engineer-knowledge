# Postmortems — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Can you turn a postmortem into prioritized, maintainable improvement work instead of an unowned action list?

---

## From factors to controls

Group contributing factors by where a control failed: prevention, detection, mitigation, or recovery. This prevents five actions that all add monitoring while none constrains a dangerous rollout.

| Finding | Weak control | Better action |
|---|---|---|
| Timeout removed in deploy | Review had no contract test | Add timeout integration test and rollout check |
| Alert arrived late | Alert measured CPU | Alert on checkout success SLI |
| Rollback took 20 min | Runbook was stale | Exercise rollback quarterly |

## Prioritize honestly

Rank actions by expected risk reduction, effort, owner capacity, and dependency. Write one outcome measure: “rollback drill restores checkout within 5 minutes,” not “improve deployment.” Link actions to the normal backlog and review overdue work at the same cadence as reliability objectives.

## Scenario

Three teams contributed to a cache invalidation incident. Rather than assigning a single “fix cache” task, create bounded actions: API team adds stale-read behavior, platform team exposes invalidation lag, and release team adds a canary check. Integration verification is a scheduled drill across all three.

## Apply it

1. Categorize four contributing factors by control type.
2. Rewrite two vague actions as an owner, deadline, and measurable outcome.
3. Identify one action that needs cross-team acceptance criteria.

## Verify your work

- Every action reduces a named failure path.
- Actions are tracked where teams plan real work.
- An integration check verifies controls together, not just separately.

## Review questions

- Why are detection-only actions often insufficient?
- How do outcome measures improve follow-through?
- When should postmortem actions be cross-team work?
