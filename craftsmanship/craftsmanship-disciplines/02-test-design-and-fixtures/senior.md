# Test Design & Fixtures — Senior

## Goal

Choose a fixture strategy that preserves confidence at system scale.

## Strategy

- Use sociable tests for coherent in-memory domain collaborators.
- Use solitary tests only where interaction is the important behavior.
- Share expensive infrastructure only with strict isolation, such as a rollback per test.
- Run the same contract suite against a fake and the production adapter.

## Control nondeterminism

- Inject a clock, random source, and ID generator.
- Make test data explicit; avoid mystery records and global state.
- Keep a small number of realistic integration paths, not a giant fixture pyramid.
