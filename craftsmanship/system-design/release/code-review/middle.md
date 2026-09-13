# Code Review — Middle

Review the change as a design, not only lines.

Trace data ownership, authorization, transaction scope, concurrency, failure, retries, and external calls. Look for unbounded work, N+1 access, sensitive logging, unsafe defaults, and interfaces that leak implementation detail.

Keep pull requests narrow enough to reason about. Separate mechanical movement from behavioral change. Ask for a design note when the diff introduces a lasting boundary or migration.

Use automation for formatting, linting, static analysis, dependency policy, tests, and secret scanning. Human review should focus on intent and judgment.

## Test yourself

1. Which boundary risks are invisible from a happy-path test?
2. Why separate mechanical and behavioral changes?
3. When does a PR need a design note?
4. Which review work should automation own?

Continue to [`senior.md`](senior.md).
