# Anti-Patterns — Middle

At middle level, diagnose the structure behind the smell.

- Shotgun surgery signals scattered responsibility.
- Feature envy signals behavior living away from the data and rules it needs.
- Over-mocking signals boundaries designed around implementation details.
- Flaky tests signal uncontrolled time, concurrency, randomness, shared state, or environment.
- N+1 access signals a mismatch between iteration and data retrieval.
- Premature abstraction signals reuse chosen before variation is understood.

Map the change path and ask which component owns the invariant. Move behavior toward that owner, introduce a seam, and verify each step. For concurrency, prefer clear ownership and message passing over shared mutable state; for async work, make task lifecycle, cancellation, and errors explicit.

## Test yourself

1. What structural cause creates shotgun surgery?
2. Which uncontrolled dependency makes a test flaky?
3. How would you prove an N+1 query exists?
4. What evidence supports extracting a shared abstraction?

Continue to [`senior.md`](senior.md).
