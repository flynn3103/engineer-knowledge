# The Legacy Change Algorithm — Senior

## Use the algorithm as a risk protocol

- The sequence is a strong default, not a ritual.
- Optimize for reversible decisions, fast feedback, and a small blast radius.
- Deviate only when you can state the risk you are accepting and why the usual step is disproportionate.

## Make the risk explicit

| Question | Evidence to gather |
| --- | --- |
| What can break? | Call graph, contracts, incident history, production traffic. |
| How will we know? | Existing tests, metrics, logs, canaries, reconciliation. |
| How far can it spread? | Consumers, data mutation, external effects, rollback path. |
| What is the safest slice? | One behavior, one boundary, one deployable increment. |

## Adjust the sequence responsibly

- Use existing monitoring as temporary feedback when a local test cannot be added before a low-risk emergency fix.
- Characterize high-value behavior before large extractions or migrations.
- Add a seam before a test when hidden dependencies block all observation.
- Wrap or sprout when direct edits would require understanding too much risky code.
- Never let “urgent” become an unexamined permanent exception; schedule the missing feedback immediately after the incident.

## Scale investigation

1. Build a short change map: entry point, data, side effects, owners, and consumers.
2. Identify one thin vertical slice that can be observed end to end.
3. Add guardrails: characterization tests, feature flags, metrics, and rollback criteria.
4. Deliver the slice, compare its behavior, then expand.

## Answer “no time for tests” with trade-offs

- Compare the test cost with the expected cost of late detection and rollback.
- Offer a bounded safety step, not an open-ended cleanup proposal.
- If time truly prevents a test, reduce scope, add monitoring, document the risk owner, and restore the feedback gap next.

## Senior heuristics

- Test behavior at the most stable boundary you can reach.
- Prefer a small, durable seam over a broad refactor.
- Use real production examples to characterize ambiguous business rules.
- Treat unexpected behavior as a discovery to validate, not a bug to “fix” by assumption.
- Stop expanding the cleanup once the requested change is safe and reviewable.

## Checklist

- [ ] The plan states the risk, feedback source, and rollback path.
- [ ] Exceptions to the algorithm are visible and time-bounded.
- [ ] The change is sliced by behavior and blast radius.
- [ ] New seams improve the next change, not just this test.
