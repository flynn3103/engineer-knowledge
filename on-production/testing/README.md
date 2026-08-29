# Testing

> The full taxonomy of automated tests — what each level catches, what it misses, and the disciplines (the pyramid, property-based testing, mutation testing, contract testing, BDD) that determine whether tests actually protect the code or just decorate it.

## Topics

| # | Topic | What you'll learn |
|---|-------|-------------------|
| 01 | [Test Strategy & the Pyramid](01-test-strategy-and-the-pyramid/junior.md) | The pyramid vs. the trophy vs. the honeycomb; what to test where; cost/confidence trade-offs |
| 02 | [Unit Testing](02-unit-testing/junior.md) | One unit, no I/O, no clock, no network; isolation, AAA, naming, fast feedback |
| 03 | [Integration Testing](03-integration-testing/junior.md) | Two or more components together; real DB vs. in-memory; Testcontainers |
| 04 | [End-to-End Testing](04-end-to-end-testing/junior.md) | The full stack from outside; brittle/slow/valuable; Playwright, Cypress, Selenium |
| 05 | [Contract Testing](05-contract-testing/junior.md) | Pact / Spring Cloud Contract; consumer-driven contracts for microservice boundaries |
| 06 | [Property-Based Testing](06-property-based-testing/junior.md) | Hypothesis, jqwik, proptest, fast-check; invariants, generators, shrinking |
| 07 | [Mutation Testing](07-mutation-testing/junior.md) | PIT, mutmut, Stryker; what mutation score actually means; testing your tests |
| 08 | [Snapshot & Approval Testing](08-snapshot-and-approval-testing/junior.md) | Jest snapshots, golden files, ApprovalTests; when they help vs. ossify |
| 09 | [Performance & Load Testing](09-performance-and-load-testing/junior.md) | k6, Locust, Gatling, JMeter; closed vs. open workload models |
| 10 | [Test Doubles: Mocks & Fakes](10-test-doubles-mocks-fakes/junior.md) | Dummy / stub / fake / spy / mock; classical vs. mockist; the over-mocking trap |
| 11 | [Test Data Management](11-test-data-management/junior.md) | Factories, fixtures, builders; seeding, anonymisation, determinism |
| 12 | [Flaky Tests & Reliability](12-flaky-tests-and-reliability/junior.md) | Root-cause taxonomy, triage playbook, quarantine, suite trust |
| 13 | [Testing in Production](13-testing-in-production/junior.md) | Canaries, synthetic monitoring, feature-flag testing, shadow traffic, chaos |
| 14 | [Acceptance & BDD](14-acceptance-and-bdd/junior.md) | Behaviour specs, Gherkin/Cucumber, executable specifications, the three amigos |

## How to use this section

Each topic has four depth levels — **junior → middle → senior → professional** — plus an **interview** Q&A bank. Start at your level and climb.

---

> Part of the [Quality Engineering](../README.md) roadmap.
