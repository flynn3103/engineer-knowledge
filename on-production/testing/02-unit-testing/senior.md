# Unit Testing — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Unit Testing** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Testing](../README.md) → Unit Testing
>
> *Khorikov's four pillars and the tensions between them; test smells; designing a suite that resists refactoring at scale.*

---

## Core Concept 1 — The Four Pillars of a Good Unit Test

Every unit test can be scored on four attributes. A test's *value* is roughly the product of the first two, weighed against the cost captured by the last two.

**1. Protection against regressions.** When a real bug is introduced into the code the test covers, does the test fail? This is the whole reason tests exist. It depends on how much code the test exercises, how complex that code is, and how meaningful the assertions are. A test that runs a lot of important logic and checks the real outcome has high regression protection. (`assert true` has none.) The honest, mechanical measure is **mutation score** — see [Mutation Testing](../07-mutation-testing/README.md).

**2. Resistance to refactoring.** When you change the code's *structure* without changing its *behavior*, does the test stay green? A test with high resistance produces a failure **only** when behavior actually breaks. The enemy here is the **false positive** — a failing test on correct code. False positives are catastrophic at scale: they train the team to ignore red, and they make every refactor expensive, so refactoring stops and the code rots. Resistance to refactoring comes almost entirely from **testing observable behavior, not implementation**.

**3. Fast feedback.** How quickly does the test run? Speed is what makes a suite *runnable on every change*. A test that takes 2 ms can run thousands of times a day; a 2-second "unit" test runs rarely and protects little. Fast feedback is why unit tests forbid I/O, network, disk, and the clock.

**4. Maintainability.** How hard is the test to read and to keep working? Two factors: how much code is in the test (setup, helpers) and how many out-of-process dependencies it touches (each one is a thing to configure and a source of flakiness). An unreadable test is a test nobody updates — and an un-updated test rots into a false negative.

```text
TEST VALUE ≈ regression-protection × resistance-to-refactoring
             ───────────────────────────────────────────────
                  weighed against feedback-speed & maintainability cost
```

A test that scores low on any single pillar is a candidate for deletion or rewrite. Low on *resistance* especially: a fragile test does active harm.

---

## Core Concept 2 — The Pillars in Tension

You cannot maximize all four. The first three trade against each other; only maintainability can be pursued freely. Understanding the trade-offs is the senior skill.

**Regression protection ↔ resistance to refactoring.** Both are about *accuracy* of the test signal — protection minimizes false negatives (missed bugs), resistance minimizes false positives (false alarms). They pull apart through **how** you reach the SUT:

- End-to-end-style tests that drive a lot of code have *high* protection but *low* resistance only if they assert on implementation; well-written, they also resist refactoring — but they're slow.
- Mockist tests that pin every interaction have *high* localization but *low* resistance to refactoring — they break on rearrangement.

**Fast feedback ↔ regression protection.** Bigger tests catch more (more code exercised) but run slower. Tiny tests are fast but each catches little. This is precisely why the **pyramid** exists: a base of fast, focused unit tests plus a thin top of slow, broad tests — see [Test Strategy & the Pyramid](../01-test-strategy-and-the-pyramid/README.md).

The one corner you can almost always win: a test that is **trivial, brittle, AND slow** has no redeeming pillar — delete it. The hard cases are the genuine three-way trade-offs.

Khorikov's key insight: **of the three competing pillars, resistance to refactoring is non-negotiable** — a test is either resistant or it isn't, and a non-resistant test is worse than no test because it generates noise. So you fix resistance first (test behavior), then trade protection against speed by choosing the test's *scope* and its place in the pyramid.

```text
        REGRESSION PROTECTION
               ╱ ╲
              ╱   ╲          pick your scope along these edges;
             ╱     ╲         RESISTANCE is mandatory, not a tradeoff
   FAST ────────────── RESISTANCE TO
 FEEDBACK              REFACTORING
```

---

## Core Concept 3 — Resistance to Refactoring at Scale

At ten tests, brittleness is annoying. At ten thousand, it's existential. A single refactor that turns 300 tests red — none for a real reason — costs days and teaches the org that refactoring is dangerous. The compounding effect:

1. Refactor triggers a wave of false positives.
2. The engineer can't tell false alarms from real failures, so they distrust *all* red.
3. They either avoid refactoring (code decays) or rubber-stamp test changes (real failures slip through).
4. The suite's signal-to-noise collapses; eventually people add `@Disabled`.

The structural causes of low resistance at scale, and the fixes:

| Cause | Fix |
|---|---|
| Mocking owned, in-process collaborators | Use real / in-memory fakes; mock only unmanaged out-of-process deps |
| Asserting on private state or call sequences | Assert on observable output and resulting state |
| Tests that mirror the production code's structure 1:1 | Test through stable public contracts, not internal seams |
| Snapshot/approval tests over volatile output | Reserve for stable, reviewed output (see [Snapshot Testing](../08-snapshot-and-approval-testing/README.md)) |
| Over-specified mocks (`verifyNoMoreInteractions`) | Verify only the interactions that *are* the contract |

The discipline that buys resistance most cheaply: **drive every test through the same public surface a real caller uses, and never let a test know anything a caller wouldn't.** When you find yourself reaching past the public API — reflection on a private field, a `@VisibleForTesting` method, an internal call assertion — treat it as a design smell, not a testing necessity. It usually means a hidden unit wants to be extracted and tested on its own public surface (Concept 6).

---

## Core Concept 4 — Designing Code for Testability

Hard-to-test code is usually badly-designed code; the test is just the messenger. The leverage is in production design, not test trickery.

**Inject dependencies; don't reach for them.** Code that calls `new Clock()`, `Database.getInstance()`, or `time.Now()` internally cannot be tested without the real thing. Pass them in.

```go
// ❌ Untestable: reaches for the clock and the DB itself.
func (s *Service) ExpireSessions() error {
    now := time.Now()
    sessions, _ := db.Global().LoadActive()
    // ...
}

// ✅ Testable: dependencies are parameters / fields.
type Service struct {
    now   func() time.Time   // injected clock
    repo  SessionRepo        // injected store
}
func (s *Service) ExpireSessions() ([]ID, error) {
    sessions, err := s.repo.LoadActive()
    if err != nil { return nil, err }
    var expired []ID
    for _, sess := range sessions {
        if sess.ExpiresAt.Before(s.now()) {
            expired = append(expired, sess.ID)
        }
    }
    return expired, nil
}
```

Now the test controls time and uses an in-memory repo — fast, deterministic, no real DB:

```go
func TestExpireSessions_ReturnsOnlyPastDeadlines(t *testing.T) {
    fixed := time.Date(2026, 1, 1, 12, 0, 0, 0, time.UTC)
    repo := &InMemorySessionRepo{sessions: []Session{
        {ID: "a", ExpiresAt: fixed.Add(-time.Hour)}, // expired
        {ID: "b", ExpiresAt: fixed.Add(time.Hour)},  // alive
    }}
    s := &Service{now: func() time.Time { return fixed }, repo: repo}

    expired, err := s.ExpireSessions()

    require.NoError(t, err)
    assert.Equal(t, []ID{"a"}, expired)
}
```

Note this test asserts on the **returned set of expired IDs** (observable behavior), not on which internal methods were called — high resistance to refactoring, and it would catch a real off-by-one in the comparison (high regression protection).

---

## Core Concept 5 — A Catalogue of Test Smells

Each smell maps to a violated pillar. Learn to name them in review.

- **Fragile test.** Breaks on behavior-preserving change. *Violates resistance.* Cause: implementation coupling.
- **Test that restates the implementation.** The assertion is the production logic copied into the test (`assert result == price * (1 - off/100)`). *Violates regression protection* — it can't catch a bug in the formula because it shares the formula. Assert against an independently-derived expected value.
- **Excessive setup / "the Mother of all fixtures."** 40 lines of arrangement for a 2-line act. *Violates maintainability* and signals the SUT has too many dependencies.
- **Assertion roulette.** A dozen unrelated assertions with no messages; when it fails, you can't tell which one. *Violates maintainability.* One behavior per test, descriptive failure messages.
- **Mystery guest.** The test depends on external data it doesn't show — a fixture file, a shared DB row, an env var. *Violates maintainability and resistance.* Make inputs explicit and local.
- **Slow unit.** A "unit" test that takes hundreds of ms — usually because it secretly touches I/O. *Violates fast feedback.* Find and remove the hidden dependency.
- **Eager test / testing everything at once.** One test exercising five behaviors. Split it.
- **Conditional logic in tests** (`if`/`for`/`try` deciding what to assert). A test with branches has untested branches of its own. Replace with parameterization.
- **Flaky test.** Non-deterministic pass/fail. *Violates everything* — see [Flaky Tests & Reliability](../12-flaky-tests-and-reliability/README.md). A flaky test is a trust leak; quarantine and fix, never ignore.

The `code-smell-detection` skill and `unit-testing-patterns` skill expand these with refactors.

---

## Core Concept 6 — Humble Object and the Functional Core

The reason some code is hard to test is that **logic is tangled with I/O**. The fix is architectural: separate the part that *decides* from the part that *acts*.

**Functional core, imperative shell.** Push all decision-making into pure functions (no I/O, no clock, no mutation of the world) — the "core." Wrap it in a thin "shell" that reads inputs, calls the core, and writes outputs. The core is trivially unit-testable (pure in/out, maximum resistance and protection). The shell is so thin it needs only a couple of integration tests.

```python
# Functional core — pure, exhaustively unit-tested.
def decide_refund(order, today) -> RefundDecision:
    if order.status != "delivered":
        return RefundDecision(allowed=False, reason="not delivered")
    if (today - order.delivered_on).days > 30:
        return RefundDecision(allowed=False, reason="window expired")
    return RefundDecision(allowed=True, amount=order.total)

# Imperative shell — thin, integration-tested, holds the I/O.
def process_refund(order_id, gateway, repo, clock):
    order = repo.get(order_id)
    decision = decide_refund(order, clock.today())      # ← all logic here
    if decision.allowed:
        gateway.refund(order.payment_id, decision.amount)
        repo.mark_refunded(order_id)
    return decision
```

`decide_refund` is where the bugs and the branches live, and it's a pure function — you can table-drive 20 scenarios against it in microseconds. The **Humble Object** pattern is the same idea applied to UI/framework shells: make the untestable layer so dumb it doesn't need testing.

---

## Core Concept 7 — Controlling Time, Randomness, and the Outside World

Determinism is a pillar prerequisite. Three classic sources of non-determinism and how to neutralize them:

- **Time.** Inject a clock (`func() time.Time`, `Clock` interface, `Instant.now()` via a `Clock` bean). Never call the global clock in testable logic. For "now-ish" assertions, assert a range, not an instant.
- **Randomness.** Inject the RNG or seed it deterministically in tests. A test that depends on real randomness is flaky by construction.
- **Concurrency / ordering.** Don't `sleep` and hope. Pull scheduling out of the logic, or test the synchronous core and leave concurrency to a dedicated, carefully-designed test.

```ts
// ✅ Vitest: freeze the clock so the test is deterministic.
import { vi, it, expect, afterEach } from "vitest";
afterEach(() => vi.useRealTimers());

it("marks a token expired one hour after issue", () => {
  vi.setSystemTime(new Date("2026-01-01T12:00:00Z"));
  const token = issueToken();                       // issued at 12:00
  vi.setSystemTime(new Date("2026-01-01T13:00:01Z")); // advance > TTL
  expect(isExpired(token)).toBe(true);
});
```

Anything you can't make deterministic doesn't belong in the unit layer — push it up to integration ([Integration Testing](../03-integration-testing/README.md)).

---

## Real-World Examples

**1. The suite that scored its own tests.** A platform team ran [mutation testing](../07-mutation-testing/README.md) over a 12,000-test module and found a 41% mutation score — most tests restated the implementation and caught nothing. High line coverage, low protection. They rewrote assertions to compare against independently-computed expected values; the mutation score rose to 78% and they *deleted* 1,500 tests that protected nothing, making the suite faster and more trustworthy at once.

**2. Refactoring rescued by resistance.** A billing engine was migrated from inheritance to composition. Because the tests asserted on computed invoices (behavior) and used real in-memory line-item objects rather than mocks, the entire 800-test suite stayed green through a structural overhaul — turning a feared rewrite into a confident afternoon.

**3. Functional core unlocking a feature.** A fraud-scoring rule lived inside a Kafka consumer (impossible to unit-test). Extracting the scoring into a pure `score(transaction) -> Risk` function let the team table-drive 60 edge cases in milliseconds; the consumer shell shrank to five lines and one integration test. The bug rate on fraud rules dropped sharply.

---

## Common Mistakes

| Mistake | Pillar violated | Fix |
|---|---|---|
| Assertion duplicates production formula | Regression protection | Compare to independently-derived expected value |
| Chasing coverage %, ignoring mutation score | Regression protection | Measure protection with mutation testing |
| Tolerating brittle tests "because they pass now" | Resistance to refactoring | Rewrite to behavior; brittle tests are net-negative |
| Hidden I/O in a "unit" test | Fast feedback | Inject dependencies; move I/O to integration |
| Logic tangled with the framework/shell | Maintainability | Extract a functional core / humble object |
| Global clock / RNG inside logic | Determinism → all pillars | Inject time and randomness |

---

## Apply it

1. State the system invariant that **Unit Testing** must protect.
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

- Which invariant must remain true when Unit Testing fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
