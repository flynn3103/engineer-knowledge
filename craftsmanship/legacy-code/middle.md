# Legacy Code — Middle

Create a seam where behavior can be observed or replaced. Extract a function, wrap a global dependency, introduce an interface at the consumer, override a factory, or move object creation to a composition root.

The legacy change algorithm is: identify change points, find test points, break dependencies, write characterization tests, make the change, then refactor under coverage.

Use “tidy first” only when a small reversible cleanup makes the feature change easier to understand. Compare the cleanup cost with reduced feature risk; do not launch a broad rewrite.

## Test yourself

1. Which dependency prevents a focused test?
2. Where can you introduce a seam without redesigning everything?
3. When is tidy-first economically useful?
4. How do you detect an accidental behavior change?

Continue to [`senior.md`](senior.md).
