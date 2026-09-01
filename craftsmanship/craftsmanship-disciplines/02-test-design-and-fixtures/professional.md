# Test Design & Fixtures — Professional

## Goal

Keep test data trustworthy in parallel CI and make flakes easy to remove.

## Standards

- Test migrations against a real disposable database when behavior depends on it.
- Use transaction rollback or isolated databases per test.
- Seed random data and control time, IDs, and external responses.
- Treat a flaky test as a defect; diagnose it instead of retrying it away.

## Triage a flake

1. Capture the seed, timing, order, and environment.
2. Reproduce with the smallest command.
3. Classify it: shared state, timing, network, randomness, or leak.
4. Remove the cause and add a check that exposes recurrence.
