# Flaky Tests & Reliability — Senior

<!-- level-focus -->
At senior level, focus on this question:

> Which system invariant is affected by **Flaky Tests & Reliability** under failure, load, and change?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Testing](../README.md) → Flaky Tests & Reliability
> *Quarantine with discipline, treat retries as a controlled poison, learn when a flaky test is screaming about a real product bug, and design flakiness out before it happens.*

---

## Core Concept 1 -- The Quarantine Pattern

When a test is flaky and you can't fix it *right now*, leaving it in the blocking suite poisons every merge — it'll randomly red-light unrelated PRs and train people to ignore CI. The disciplined move is **quarantine**: pull it out of the merge-gating set so it stops blocking, but keep running it on a separate track so you don't lose sight of it.

```python
# Mark the test so CI excludes it from the blocking suite but still runs & reports it.
import pytest

@pytest.mark.quarantine     # custom marker; CI runs these non-blocking
def test_payment_webhook_roundtrip():
    ...
```

```yaml
# CI: blocking job excludes quarantine; a separate non-blocking job runs them.
- name: blocking-tests
  run: pytest -m "not quarantine"          # gates the merge
- name: quarantined-tests
  run: pytest -m quarantine || true        # reports, never blocks
  continue-on-error: true
```

Quarantine **restores trust in the blocking suite** immediately: now red on the gate means a real problem again. The flaky test keeps running so you still see whether it's getting better or worse. What you must *not* do is delete it silently (you lose the coverage and the signal) or leave it blocking (you keep eroding trust).

## Core Concept 2 -- The Quarantine Discipline: TODO, Not Graveyard

Quarantine is dangerous precisely because it works *too well*. Once the pain of a blocking flake is gone, the incentive to fix it evaporates. Quarantine quietly becomes a **graveyard** of "temporarily" disabled tests — coverage you think you have but don't.

The discipline that prevents this:

- **Every quarantined test has an owner.** A name, not "the team." Unowned means unfixed.
- **Every quarantined test has a tracking ticket** linked from the code, treated as a real bug.
- **Every quarantined test has a deadline.** Two weeks, a sprint — pick a number and enforce it.
- **Auto-expiry.** If a test sits in quarantine past its deadline, escalate it or delete it — don't let it rot.

```python
@pytest.mark.quarantine(
    owner="bakhodir",
    ticket="QE-1423",
    deadline="2026-07-05",        # CI fails the build if this date passes
)
def test_payment_webhook_roundtrip():
    ...
```

> **Quarantine is a TODO with a deadline, not a place tests go to die.** A quarantine list that only grows is a sign of a team that has given up on its suite. Periodically review it; a healthy program keeps it small and moving.

The economics matter too: a quarantined test provides *zero* gate protection. The longer it stays out, the longer that code path is effectively untested. Treat the quarantine queue with the same urgency as a production-bug queue.

## Core Concept 3 -- Retries: The Double-Edged Sword

Auto-retry — "re-run the failed test up to N times; pass if any attempt is green" — is the most tempting and most dangerous tool in this topic.

```yaml
# JVM example: Gradle test-retry plugin
test {
  retry {
    maxRetries = 2
    maxFailures = 10           # disable retries if too many tests are failing
    failOnPassedAfterRetry = false
  }
}
```

The danger is brutal and concrete: **a green-on-retry hides flakiness *and* hides real race conditions.** Suppose production code has a 1-in-50 data race. A single run catches it 2% of the time — annoying but a genuine signal. Add 2 retries and the chance all three attempts hit the race drops to ~1-in-125,000. The test now goes green ~99.999% of the time. **You have not fixed the race. You have hidden a real production bug behind retries**, and shipped it.

So when are retries acceptable?

- **Acceptable, with limits:** end-to-end tests against networks/third-party systems you don't control, where transient infra failures are unavoidable. Even here: cap retries low (1-2), and **always record the retry rate**.
- **Not acceptable:** unit and integration tests of *your own* logic. A flaky unit test means your code or your test has a determinism bug. Retrying it masks exactly the bug you wrote the test to catch.

The non-negotiable rule: **if you retry, you must measure the retry rate and surface it.** A test that "passes" only after retries is not green — it's amber, and a rising retry rate is a leading indicator of a real bug or a degrading suite. A silent retry is a lie told to the whole team.

## Core Concept 4 -- When a Flaky Test Reveals a Real Bug

The deepest insight in this topic: **sometimes the test isn't flaky — the product is.**

A test that fails 1-in-N times because of a real data race, a real timeout that's *almost* always met, or a real ordering assumption in the code is doing its job perfectly. It is the only thing standing between you and an intermittent production incident. If you "stabilize" it by adding a sleep, a retry, or a quarantine, you have:

1. Silenced your only detector of a live bug.
2. Shipped a system that will fail intermittently for *users* instead of for CI.

```go
// The flaky test:
func TestCounterConcurrent(t *testing.T) {
    c := &Counter{}
    var wg sync.WaitGroup
    for i := 0; i < 1000; i++ {
        wg.Add(1)
        go func() { defer wg.Done(); c.Inc() }()
    }
    wg.Wait()
    require.Equal(t, 1000, c.value)   // sometimes 997, 998... FLAKY
}
```

The wrong response is "add a mutex around the test" or retry. The right response is `go test -race`, which points at the *product*:

```go
// The REAL bug the flaky test was catching:
func (c *Counter) Inc() { c.value++ }            // ❌ unsynchronized — data race

// The actual fix — in PRODUCTION code, not the test:
func (c *Counter) Inc() { atomic.AddInt64(&c.value, 1) }   // ✅
```

> Before you stabilize a flaky test, ask: **"is the test wrong, or is the product wrong?"** Reach for `go test -race` / ThreadSanitizer and the `concurrency-patterns` skill. Stabilizing the test when the product is flaky is how intermittent outages reach production. (Cross-ref concurrency.)

This is also the strongest argument *against* blanket auto-retry: it systematically converts "the product is flaky" into "CI is green," which is the worst possible outcome.

## Core Concept 5 -- Prevention by Design: Determinism Seams

The cheapest flaky test is the one that can't exist. Seniors prevent whole categories by building **determinism seams** into the code under test — injectable boundaries for every non-deterministic input.

- **Time.** Never call `time.Now()` / `Date.now()` directly in business logic. Inject a `Clock`. Tests pass a fixed or fake clock; no flakiness from boundaries, timezones, or DST. (See [Test Doubles](../10-test-doubles-mocks-fakes/senior.md).)
- **Randomness.** Inject the RNG (or seed it). Production uses a secure/real source; tests pass `Random(seed)`.
- **Network/I-O.** Inject the HTTP client / repository so tests substitute a fake. No real network in unit tests means no network flakiness. (Cross-ref test-doubles.)
- **Concurrency.** Provide deterministic hooks — done channels, completion callbacks, controllable schedulers — so tests wait on real events, not sleeps. (Cross-ref E2E for explicit waits.)
- **Collections.** Return sorted or canonicalized output where order isn't semantically meaningful, so callers (and tests) never depend on iteration order.

```typescript
// Determinism seam for time — the single most valuable one to add.
interface Clock { now(): Date }
class SystemClock implements Clock { now() { return new Date() } }
class FixedClock implements Clock {
  constructor(private t: Date) {}
  now() { return this.t }
}
// Production: new TokenService(new SystemClock())
// Test:       new TokenService(new FixedClock(new Date("2026-01-01")))
```

Design seams in, and the async/timing, non-determinism, and external-dependency families of flakiness mostly evaporate at the source.

## Core Concept 6 -- Hermetic Tests & Isolation by Construction

A **hermetic** test depends on nothing it doesn't control: no shared DB, no real clock, no network, no global state. Hermeticity is the structural cure for ordering, isolation, and external-dependency flakiness.

Build it in by construction, not by cleanup-after-the-fact:

- **Per-test isolation.** Each test gets a fresh schema/namespace, or runs inside a transaction rolled back at teardown. Containerized ephemeral databases (Testcontainers) give every run a clean instance. (See [Integration Testing](../03-integration-testing/senior.md).)
- **Unique resources.** Bind to ephemeral ports (`:0`), use unique temp dirs and random key prefixes so parallel tests never collide.
- **No shared mutable singletons in tested code.** Inject dependencies; reset any unavoidable statics in setup, not just teardown (so a previous crash can't poison you).
- **Independent test data.** Each test creates exactly the data it needs and owns its lifecycle. (See [Test Data Management](../11-test-data-management/senior.md).)

Hermetic tests are also a prerequisite for safe parallelism: you can only run tests in parallel if none of them share mutable state.

## Core Concept 7 -- Triage: Fix, Quarantine, or Delete

When a flake surfaces, a senior runs a fast decision:

```
Is the PRODUCT flaky (real race/timeout)?  → YES → fix the product. STOP. (Concept 4)
Can I fix the test cheaply now?            → YES → fix it (taxonomy). Done.
Is it blocking merges and not cheap?       → YES → QUARANTINE (owner+ticket+deadline).
Is the test low-value / redundant / costly to keep deterministic? → DELETE it.
```

**When to delete rather than fix.** Not every test is worth saving. Delete when: the test is redundant with cheaper coverage; it tests behavior no longer worth asserting; or making it deterministic would cost more than the bug it could catch. A deleted low-value flaky test is *better* than a quarantined one rotting forever — but deletion is a deliberate, reviewed decision with a rationale, never a stealth `@skip`.

> The cardinal sin is the *non-decision*: a flaky test left blocking, or silently skipped, with no owner and no plan. Every flake gets a verdict.

## Core Concept 8 -- Measuring Suite Reliability Over Time

You manage reliability as a trended metric, not a vibe.

- **Suite pass rate** — fraction of CI runs green without intervention (reruns/quarantine). Trend it weekly; a falling pass rate means trust is leaking.
- **Per-test flakiness rate** — `failures / runs` per test. Rank tests; the worst offenders get triaged first.
- **Retry rate** — how often any test passes only after a retry. A rising retry rate is a leading indicator of a real bug or a degrading suite.
- **Quarantine size & age** — how many tests are quarantined and how long. Should stay small and move; a growing, aging queue signals surrender.

Feed these into a dashboard and review them as a team. Reliability that isn't measured silently decays — every flake nudges the team one step closer to ignoring red. (See [Engineering Metrics & DORA](../../engineering-metrics-and-dora/) for treating reliability as a first-class metric.)

## Real-World Examples

- **Retry hid an outage.** A service had a 1-in-40 race in connection handling. CI ran with 3 retries, so it was green ~99.998% of the time. The race manifested in production as intermittent 500s under load. Removing retries turned the flake back red, `-race` found the bug in a day. The retry config had been hiding a real incident for months.
- **Quarantine graveyard.** A monorepo accumulated 380 quarantined tests over two years with no deadlines. Nobody knew which code paths were actually covered. The cleanup project deleted half (redundant/obsolete) and fixed the rest — and instituted a 14-day quarantine expiry so it could never happen again.
- **The seam that ended a class of flakes.** A team introduced a `Clock` interface across the codebase. Every date/expiry/scheduling test became deterministic overnight; a recurring family of "midnight" and "DST" flakes simply stopped occurring.

## Common Mistakes

- **Quarantine without deadline/owner** → permanent graveyard, silent coverage loss.
- **Blanket auto-retry on all tests** → systematically converts product bugs into green builds.
- **Stabilizing a test that's catching a real race** → ships the race to users.
- **Reading the real clock/RNG/network in tested code** → flakiness you'll fight forever instead of injecting once.
- **No reliability metrics** → you discover trust is gone only after the team already ignores red.
- **Silent `@skip` instead of a reviewed delete** → undocumented coverage hole.

---

## Apply it

1. State the system invariant that **Flaky Tests & Reliability** must protect.
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

- Which invariant must remain true when Flaky Tests & Reliability fails?
- Where should recovery responsibility live, and why?
- Which assumption deserves an experiment before implementation?
- How can the design evolve without changing every consumer at once?
