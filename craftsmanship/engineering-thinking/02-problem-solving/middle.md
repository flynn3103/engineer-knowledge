# Problem-Solving — Middle

Middle-level problems have multiple plausible causes and cross component boundaries.

## Build a hypothesis tree

Break “checkout fails” into client validation, API behavior, application rules, database state, payment dependency, and asynchronous completion. Rank hypotheses by explanatory power, probability, test cost, and risk.

## Devise a reversible plan

A good plan states the invariant, stages, evidence, rollback, and stop condition. Separate diagnosis from implementation: first locate the failing boundary, then change it.

Use logs at component boundaries, correlation IDs, traces, database query evidence, and controlled fault injection. Compare a failing case with the nearest healthy case.

## Execute and reflect

Keep a decision log: observation, hypothesis, test, result, next step. After resolution, ask why detection was slow, which guardrail was missing, and whether the mental model or the system needs correction.

## Test yourself

1. How do you rank two equally plausible hypotheses?
2. What makes a plan reversible?
3. Which boundary evidence would isolate an API-to-database failure?
4. What learning belongs in a test versus a runbook?

Continue to [`senior.md`](senior.md).
