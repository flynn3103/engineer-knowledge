# The Legacy Change Algorithm — Professional

## Turn the algorithm into team practice

- Make safe change the default delivery process, not an individual heroics exercise.
- Estimate characterization, seams, and verification as part of the feature that needs them.
- Track whether the next comparable change becomes faster and less incident-prone.

## Slice legacy work into reviewable PRs

1. **Discover:** map the requested behavior and its risks.
2. **Characterize:** add tests or production-safe observation for current behavior.
3. **Enable:** introduce the smallest seam or wrapper needed.
4. **Change:** deliver the requested behavior behind a clear boundary or flag.
5. **Simplify:** refactor only after the behavior is protected.

Each PR should state its purpose, evidence, risk, and rollback condition. Avoid a single “refactor legacy module” PR that reviewers cannot safely reason about.

## Review legacy-change PRs for evidence

- Does the PR name the behavior being preserved and the behavior changing?
- Are tests based on real domain examples and observable outcomes?
- Is new indirection limited to a useful seam?
- Did the author separate safety work from unrelated cleanup?
- Can the change be rolled back without corrupting data or hiding an incident?
- Are any untested assumptions called out for follow-up?

## Give teams a decision guide

| Condition | Default action |
| --- | --- |
| Hot and risky area | Characterize before changing. |
| Change is isolated by a clean boundary | Wrap or strangle incrementally. |
| New behavior can be separate | Sprout a tested method or class. |
| Stable, low-risk area | Defer investment until there is business pull. |
| Emergency change | Minimize scope, monitor closely, then close the feedback gap. |

## Coordinate over time

- Keep a lightweight map of hotspots, owners, known seams, and pending follow-ups.
- Share captured behavior with domain experts; executable examples survive turnover better than memory.
- Prevent parallel changes from crossing the same risky boundary without an explicit owner and integration plan.
- Use incident reviews to find where the algorithm was skipped or feedback was too slow.

## Team pitfalls

- Measuring success only by line coverage instead of safe delivery.
- Treating characterization tests as permission to preserve harmful behavior forever.
- Allowing a “temporary” bypass to become a permanent untested path.
- Starting an unfunded rewrite instead of improving the next valuable change.
- Punishing engineers for surfacing uncertainty in behavior they are responsibly discovering.

## Operating checklist

- [ ] Teams know the five steps and when to use sprout or wrap.
- [ ] Feature plans account for feedback work in risky areas.
- [ ] PR templates ask for preserved behavior, changed behavior, and rollback.
- [ ] Hotspots are prioritized by business pull, risk, and churn.
- [ ] The organization measures whether changes become safer and faster over time.
