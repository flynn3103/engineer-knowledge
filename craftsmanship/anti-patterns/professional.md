# Anti-Patterns — Professional

Professional practice treats anti-patterns as outcomes of incentives, architecture, and feedback—not individual carelessness.

Google’s monorepo tooling uses large-scale refactoring and presubmit checks to make sweeping API migrations reviewable. Netflix’s resilience practices expose retry, timeout, and fallback behavior because hidden coordination failures amplify under load. Kubernetes API evolution uses versioned schemas, conversion, and deprecation policy because breaking distributed consumers cannot be solved by a local refactor.

At 10× scale, review and test feedback become bottlenecks. At 100×, ownership ambiguity and compatibility dominate. Track change failure, flaky-test rate, dependency cycles, hotspot concentration, queue growth, and migration age.

## Design and operations checklist

1. Name observed harm, not only the smell label.
2. Identify incentives and constraints sustaining it.
3. Establish behavior and operational baselines.
4. Add a seam and rollback before migration.
5. Automate a ratchet where the rule is objective.
6. Assign ownership and removal criteria to temporary paths.

```text
PRESSURE -> LOCAL SHORTCUT -> SYSTEM COST -> MORE PRESSURE
                  break with evidence + seams + ratchets + ownership
```

## Test yourself

1. Design a ratchet for a repository with 500 existing dependency violations.
2. Which metric separates an isolated smell from a systemic hotspot?
3. How would you migrate a shared API used by hundreds of consumers?
4. What incentive may recreate the anti-pattern after cleanup?

## Further reading

- Martin Fowler, *Refactoring*.
- Michael Feathers, *Working Effectively with Legacy Code*.
- Joshua Kerievsky, *Refactoring to Patterns*.
- Google Engineering Practices documentation on large changes and review.
