# Test Doubles: Mocks & Fakes

Use test doubles to control dependencies while preserving the behavior that a test needs to prove.

## Learn by level

- [Junior](junior.md) — distinguish dummies, stubs, fakes, spies, and mocks.
- [Middle](middle.md) — choose a double without coupling to implementation details.
- [Senior](senior.md) — keep shared fakes aligned with real systems.
- [Professional](professional.md) — set team conventions that avoid over-mocking.

## Apply it

1. Identify the dependency you need to control.
2. Choose the simplest double that supports the behavior under test.
3. Assert outcomes before asserting interactions.
4. Verify external boundaries with integration or contract tests.
