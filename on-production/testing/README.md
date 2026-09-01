# Testing

Use this roadmap to choose the smallest test that can prove the behavior you need.

## Topics

- [Test Strategy & the Pyramid](test-strategy-and-the-pyramid/README.md) — place checks at the right level.
- [Unit Testing](unit-testing/README.md) — verify focused logic quickly and deterministically.
- [Integration Testing](integration-testing/README.md) — verify real boundaries such as databases and HTTP clients.
- [End-to-End Testing](end-to-end-testing/README.md) — protect the critical user journeys.
- [Contract Testing](contract-testing/README.md) — keep service boundaries compatible.
- [Property-Based Testing](property-based-testing/README.md) — test invariants across many generated inputs.
- [Mutation Testing](mutation-testing/README.md) — measure whether tests detect meaningful faults.
- [Snapshot & Approval Testing](snapshot-and-approval-testing/README.md) — review stable, high-value outputs.
- [Performance & Load Testing](performance-and-load-testing/README.md) — validate response time and capacity under load.
- [Test Doubles: Mocks & Fakes](test-doubles-mocks-fakes/README.md) — choose substitutes without hiding important behavior.
- [Test Data Management](test-data-management/README.md) — create safe, deterministic data for tests.
- [Flaky Tests & Reliability](flaky-tests-and-reliability/README.md) — find, fix, and prevent unreliable checks.
- [Testing in Production](testing-in-production/README.md) — learn safely from live systems.
- [Acceptance & BDD](acceptance-and-bdd/README.md) — turn shared behavior into executable examples.

## How to use the guides

1. Start with the topic closest to the failure you want to prevent.
2. Read the level that matches the responsibility you own today.
3. Apply one checklist or example to a real change.
4. Use the review questions at the end of each guide to confirm understanding.

## Levels

- **Junior:** Run a clear test and explain what it proves.
- **Middle:** Choose a suitable test boundary and verify the integrated behavior.
- **Senior:** Protect system invariants under failure, change, and scale.
- **Professional:** Establish reliable team practices with measurable outcomes.

> Part of the [On Production](../README.md) roadmap.
