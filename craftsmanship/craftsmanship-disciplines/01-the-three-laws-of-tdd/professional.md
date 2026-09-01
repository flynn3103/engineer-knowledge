# The Three Laws of TDD — Professional

## Goal

Make test-first work reliable across a team and in continuous delivery.

## Team practices

- Keep unit tests fast and deterministic; isolate slow integration checks.
- Require a regression test for each production defect.
- Review behavior and failure quality, not only coverage.
- Run relevant tests locally and the full safety net in CI.

## Useful signals

- Time from edit to feedback.
- Flaky-test rate and time spent investigating flakes.
- Escaped defects and the tests that would have caught them.
- Mutation-test results for critical rules, used as a sample rather than a target.

## Avoid

- Treating line coverage as proof of correctness.
- Mocking every collaborator until refactoring becomes impossible.
- Letting a slow suite turn red-green-refactor into a ceremony.
