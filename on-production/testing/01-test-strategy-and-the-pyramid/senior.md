# Test Strategy & the Pyramid — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Test Strategy & the Pyramid** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Testing](../README.md) → Test Strategy & the Pyramid
> *Designing a risk-based test strategy for a real system under a real CI budget — not drawing a triangle.*

---

## Core Concept 1 -- Strategy as risk allocation, not shape worship

Testing is a *budget allocation problem*. You have finite engineer-hours to write tests and finite CI-minutes to run them. The goal is to **maximise confidence per unit cost**, where confidence means "we will catch the defects that matter before they ship."

Two systems with identical architectures can warrant different strategies because their *risk profiles* differ. A reporting dashboard and a payment ledger may both be "a service + a DB," but a wrong number means a stale chart in one case and a financial loss in the other. Strategy starts by asking, for *this* system:

- **Where will defects occur?** (Complex logic, churny code, weak boundaries, integration points, concurrency.)
- **Where will defects hurt?** (Money, safety, data integrity, legal/compliance, reputation, irreversibility.)
- **What can we afford to run, every commit?** (The CI budget.)

The shape is the *answer*, not the question.

## Core Concept 2 -- Building the risk map

Make the risk explicit. A lightweight table per major area beats intuition:

```text
Area            Likelihood  Impact   Where bugs live        -> Test emphasis
-----------------------------------------------------------------------------
Pricing engine    High       High    deep branching logic    unit (exhaustive) + property-based
Payment gateway   Med        Crit    external API, retries   integration + contract + a few E2E
Auth / sessions   Med        Crit    token expiry, edge time small (faked clock) + integration
Report rendering  High       Low     CSS/layout              minimal automated; manual/visual spot
Admin CRUD        Low        Low     framework boilerplate    thin integration only
Search ranking    High       Med     scoring math            unit + property-based; snapshot for output
```

Likelihood and impact are coarse (High/Med/Low) on purpose — precision here is false. The output is *emphasis*: where to spend exhaustive coverage, where a thin smoke test suffices, where automation isn't worth it at all. Note two non-obvious moves: high-likelihood/low-impact areas (report layout) get *less* automation than instinct suggests, and low-likelihood/critical areas (payments) still get heavy coverage because the impact dominates.

Property-based testing earns a place wherever logic is rich (pricing, search ranking, parsers) — it covers input space that example tests miss. (See [Property-Based Testing](../06-property-based-testing/).)

## Core Concept 3 -- The CI time budget is a hard constraint

A strategy that ignores wall-clock time is a fantasy. Define the budget first, then design within it.

**A worked budget.** Say the team's rule is: *pre-merge checks must finish in under 10 minutes* (the threshold above which engineers context-switch and PRs stall). Assume 8-way CI parallelism.

```text
Budget: 10 min wall-clock, 8 parallel shards  =>  ~80 min total test-CPU

Allocate the 80 min of test-CPU:
  Unit (small)        : 5,000 tests × 5 ms     =  25 s   -> trivial, run all every shard
  Integration (medium): 600 tests   × 400 ms   = 240 s   = 4.0 min CPU
  Contract            : 80 tests     × 300 ms   =  24 s
  E2E (large)         : 25 tests     × 12 s     = 300 s   = 5.0 min CPU
                                                  --------
                                       total CPU = ~9.8 min  /8 shards = ~1.2 min wall
```

The arithmetic reveals the real cost driver instantly: **25 E2E tests cost more CPU than 5,000 unit tests.** That is the pyramid argument made quantitative — and it tells you exactly how many E2E tests you can afford. If product wants 200 E2E tests, the math says the budget breaks (200 × 12 s = 40 min CPU = 5 min wall on its own, *before* everything else), so either the budget grows, parallelism grows, or the E2E count is wrong. The budget converts vague "too many E2E" arguments into numbers.

## Core Concept 4 -- Designing the layer allocation from the budget

Given the risk map and the budget, derive counts top-down — because the **top is the scarce resource**:

1. **Decide the E2E set first.** It is the most constrained (slowest, flakiest). List the *critical journeys* — the flows whose breakage is unacceptable. For most systems that is 5–30 flows, not 200. Each becomes one E2E test of the happy path; its edge cases go *down*.
2. **Decide contract coverage at every cross-service seam.** One consumer-driven contract per (consumer, provider) pair you depend on.
3. **Cover wiring and I/O with integration tests** — one or a few per repository/adapter/handler, proving the real round-trip works.
4. **Push everything else down to small tests** — exhaustively, because they're nearly free.

This is why the suite *ends up* pyramid-shaped for logic-heavy systems and *diamond*-shaped (fat integration) for thin services: the shape is the residue of "E2E is scarce, so spend it last and least."

```text
DERIVED SHAPE for a logic-rich payments service (within the 10-min budget):

   E2E         25      |#                       critical journeys only
   Contract    80      |###
   Integration 600     |##########              every seam + adapter
   Unit       5000     |######################  all logic, exhaustively
```

## Core Concept 5 -- Eliminating redundant coverage

Redundant coverage is the most common silent cost in a mature suite: the same behaviour asserted at unit *and* integration *and* E2E. It triples runtime and maintenance while adding zero confidence (a bug in that behaviour was already catchable lower down).

The senior discipline: for each behaviour, ask **"what is the *lowest* level that can fail if this breaks?"** and cover it *there only*. Higher levels assert *different* things:

```text
Behaviour: "orders over $100 get free shipping"
  unit         : the rule itself, all boundaries ($99.99, $100.00, $100.01)   <- cover HERE
  integration  : the order, once saved and reloaded, still computes shipping   <- WIRING, not the rule
  E2E          : a user checking out a $120 cart sees "Free shipping"          <- JOURNEY, not the rule

Anti-pattern: re-testing $99.99/$100.00/$100.01 at all three levels.
```

A periodic audit — "which E2E tests assert logic already covered by unit tests?" — typically lets you delete a third of a legacy E2E suite with no loss of confidence and a large CI speedup.

## Core Concept 6 -- Contracts and the seam strategy

For distributed systems, the strategic move is to **replace cross-service E2E with contract tests.** Booting N services to verify A talks to B is slow, flaky, and scales combinatorially. Contract testing splits that verification:

- The **consumer** records its expectations of the provider (the requests it sends, the responses it needs) as a contract.
- The **provider** is tested *in isolation* against that contract (provider verification).

Each side runs as a fast small/medium test; together they guarantee the seam holds without ever booting both. This is what lets the honeycomb/diamond keep its "integrated" top thin. Reserve true multi-service E2E for a *handful* of smoke tests that prove the environment assembles at all. (Full treatment in [Contract Testing](../05-contract-testing/).)

## Core Concept 7 -- Coverage is an input, risk is the driver

Line/branch coverage is a *diagnostic*, not a *target*. Two failure modes of coverage-driven testing:

1. **Goodhart's law.** When coverage becomes the goal, engineers write assertion-free tests that execute lines without checking behaviour — 90% coverage, near-zero confidence. (See [Mutation Testing](../07-mutation-testing/) for measuring whether tests actually assert anything.)
2. **Uniform coverage misallocates risk.** "80% everywhere" spends as much effort on trivial getters as on the pricing engine. Risk-based testing deliberately over-covers the dangerous parts and under-covers the trivial ones — which may *lower* a global coverage number while *raising* real safety.

Use coverage to find *gaps* in code you've decided is risky ("the pricing engine is only 60% covered — that's a problem"), never as the strategy itself. Coverage lives in its own QE section precisely because it is a measurement, not a kind of test — see [Code Coverage](../../code-coverage/).

## Core Concept 8 -- Flakiness as a first-class budget line

A flaky test is worse than no test: it trains engineers to ignore red, and re-runs burn the CI budget you carefully designed. Flakiness scales with test *size* — the more real network/disk/clock/concurrency a test touches, the more ways it fails for non-reasons. So the strategy must **account for flakiness when allocating up the pyramid:**

```text
Effective cost of an E2E test = run_time × (1 + expected_reruns)
  A 12 s E2E with a 5% flake rate, retried twice on failure,
  costs on average ~12 s + 0.05 × 2 × 12 s ≈ 13.2 s  -- and worse, erodes trust.
```

Budget a **flake rate ceiling** (e.g. < 1% per test, < 0.1% suite-level) and quarantine offenders rather than blanket-retrying. Track it. A rising flake rate is the leading indicator that the suite is drifting up the pyramid into the cone. (See [Flaky Tests & Reliability](../12-flaky-tests-and-reliability/).)

## Real-World Examples

**Redesigning a 28-minute suite.** A team's CI runs 28 minutes and flakes ~8%. Audit finds 220 Selenium tests, ~70% of which re-assert validation/business rules already (or easily) covered lower down. Plan: keep 18 journey E2E tests, move logic to ~900 new unit tests, add 40 contract tests for the three downstream services, quarantine the 12 flakiest E2E tests on day one. Outcome: 7-minute CI, < 1% flake, *more* escaped-defect coverage than before.

**A thin notifications microservice.** Almost no logic — receive event, template a message, call a provider. Risk map says bugs live at the provider seam and in templating. Strategy: minimal unit tests (template rendering), a fat integration layer (event → provider with the provider faked), one contract with the upstream event producer, zero E2E (covered by the platform's smoke suite).

**Adding a risky pricing rewrite.** New tax engine, high likelihood × high impact. Strategy bumps this *one area*: exhaustive unit tests plus property-based tests asserting invariants ("tax is never negative," "subtotal + tax = total"), even though the rest of the service stays thinly tested. Risk-based, not uniform.

## Common Mistakes

- **Drawing the shape first, fitting reality second.** The shape must be derived from risk + budget, not imposed.
- **Uniform coverage targets.** "80% everywhere" guarantees you over-test the trivial and under-test the dangerous.
- **Ignoring CI wall-clock.** A correct-on-paper strategy that makes CI take 40 minutes will be abandoned in practice.
- **Booting the world for seam tests.** Multi-service E2E where contract tests would do — slow, flaky, combinatorial.
- **Blanket-retrying flakes.** Hides rot and burns budget; quarantine and fix instead.
- **Never auditing redundancy.** Mature suites accrete duplicate coverage; without periodic pruning the suite gets slower with no added safety.

---

## Apply it

1. State the system invariant that **Test Strategy & the Pyramid** must protect.
2. Mark ownership, state, and failure propagation at each boundary.
3. Compare two designs under load, dependency failure, and future change.
4. Define recovery and compatibility behavior before implementation.
5. Test the riskiest assumption with a focused experiment.

## Verify your work

- The experiment supports the design with evidence, not preference.
- Failure injection shows the blast radius and recovery path.
- Compatibility checks cover old and new callers or data.
- Operational signals reveal invariant violations and recovery progress.

## Review questions

- Which invariant must remain true when Test Strategy & the Pyramid fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
