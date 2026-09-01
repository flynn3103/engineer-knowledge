# The Three Laws of TDD — Middle

## Goal

Choose small tests that expose design choices without slowing the loop.

## Reaching green

- Fake it: return a constant when it is the quickest honest step.
- Obvious implementation: write the direct solution when it is simpler.
- Triangulate: add examples that force a general rule.

## Design pressure

- Test behavior, not private methods.
- Put databases, clocks, queues, and HTTP behind small interfaces.
- Use a fake or stub at a slow boundary; keep domain logic real.

## Bug-fix loop

1. Reproduce the defect with a failing test.
2. Make only that test pass.
3. Add nearby cases if they reveal a missing rule.
4. Refactor after green.

## Review checklist

- Did the test fail before the change?
- Does each test state one useful behavior?
- Is the suite fast enough to run continuously?
