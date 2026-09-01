# Evaluation and Execution Models — Junior

Eager evaluation computes arguments before a call; lazy evaluation delays work until demanded. Call-by-value passes a computed value, though that value may be a reference. Short-circuit boolean operators conditionally skip expressions.

The naive assumption “lines run top to bottom” breaks with callbacks, generators, async tasks, and optimizer transformations.

## Test yourself

1. Which expression is skipped by short-circuiting?
2. Does passing a reference copy the object?
3. When does a generator body run?

Continue to [`middle.md`](middle.md).
