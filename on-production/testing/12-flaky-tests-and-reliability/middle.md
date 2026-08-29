# Flaky Tests & Reliability — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Flaky Tests & Reliability** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Testing](../README.md) → Flaky Tests & Reliability
> *Master the root-cause taxonomy of flakiness — async, ordering, isolation, concurrency, non-determinism, external deps, leaks, environment — and learn to detect and measure it instead of guessing.*

---

## Core Concept 1 -- The Root-Cause Taxonomy

Every flaky test traces to one of these eight families. Internalize this list — it's the spine of the whole discipline.

| # | Root cause | Smell | One-line fix |
|---|-----------|-------|-------------|
| 1 | **Async / timing** | `sleep(n)`; "works locally, fails in CI" | Poll for a condition with a timeout |
| 2 | **Order & shared state** | Passes in suite, fails alone (or vice versa) | Make tests independent; reset state |
| 3 | **Isolation failure** | Leaked singletons, static fields, stray DB rows | Per-test isolation/transactions; reset statics |
| 4 | **Concurrency / races** | Fails ~1/N runs, no pattern | Fix the real race (in test *or* product) |
| 5 | **Non-determinism** | Random/time/map-order/locale in assertions | Seed it; inject a clock; sort; pin locale |
| 6 | **External dependencies** | Fails on network/3rd-party hiccup | Stub the dependency; make it hermetic |
| 7 | **Resource leaks/exhaustion** | Fails late in the run, ports/FDs/memory | Close resources; bound pools; clean up |
| 8 | **Environment differences** | CI vs. local, OS, timezone, container | Pin/normalize the environment |

> Mental shortcut: when a test flakes, walk the table top to bottom and ask "could it be *this*?" The first match is usually right.

## Core Concept 2 -- Async & Timing

The most common family. The work happens asynchronously and the test guesses how long to wait.

```go
// ❌ FLAKY: fixed sleep races the goroutine
func TestCacheWarmup(t *testing.T) {
    cache.WarmAsync()
    time.Sleep(100 * time.Millisecond) // guess
    if !cache.IsWarm() {
        t.Fatal("cache not warm")
    }
}

// ✅ STABLE: poll until ready, bounded by a timeout
func TestCacheWarmup(t *testing.T) {
    cache.WarmAsync()
    require.Eventually(t, cache.IsWarm, 5*time.Second, 10*time.Millisecond)
}
```

`require.Eventually` (testify) polls every 10 ms up to 5 s. **Recognize it** by `sleep` calls and the "works on my machine" signature. **Fix it** by waiting on the actual post-condition — a status, a row, an element. Even better, expose a deterministic hook (a callback, a channel, a done signal) so the test waits on a *real event* rather than polling.

## Core Concept 3 -- Test Ordering & Shared State

A test passes only because of what ran before it, or fails because a sibling polluted shared state.

```python
# ❌ FLAKY (order-dependent): relies on a module-level list
USERS = []

def test_add_user():
    USERS.append("alice")
    assert len(USERS) == 1          # passes only if run first

def test_count_users():
    assert len(USERS) == 1          # passes only if test_add_user ran first
```

Run these in a different order (or in parallel) and they fail. **Recognize it** with the rule: *a test that passes in the suite but fails when run alone — or fails when the suite is shuffled — is order-dependent.* Modern runners can shuffle order to expose this (`pytest -p randomly`, `go test -shuffle=on`).

```python
# ✅ STABLE: each test owns its state
def test_add_user():
    users = []
    add_user(users, "alice")
    assert len(users) == 1

def test_count_users():
    users = ["alice"]
    assert count(users) == 1
```

The principle: **every test must set up its own world and tear it down.** Never let global lists, caches, or env vars carry data between tests.

## Core Concept 4 -- Isolation Failures: Leaked Singletons, Static & DB State

A subtler cousin of ordering: state leaks through singletons, static fields, or a shared database.

```python
# ❌ FLAKY: a leaked singleton remembers the previous test
class FeatureFlags:        # process-wide singleton
    _instance = None
    enabled = set()

def test_premium_on():
    FeatureFlags.instance().enabled.add("premium")
    assert is_premium_visible()      # leaves "premium" enabled!

def test_premium_off_by_default():
    assert not is_premium_visible()  # fails if test_premium_on ran first
```

The singleton carries `premium` into the next test. **Fix:** reset shared state in teardown, or — better — don't use a process-wide singleton in tested code; inject the dependency so each test gets a fresh instance (see [Test Doubles](../10-test-doubles-mocks-fakes/middle.md)).

For databases, the canonical fix is **transaction rollback** or **truncate-per-test**:

```python
# ✅ STABLE: each test runs in a transaction that is rolled back
@pytest.fixture
def db():
    conn = engine.connect()
    txn = conn.begin()
    yield conn
    txn.rollback()        # nothing leaks to the next test
    conn.close()
```

Stray rows from one test changing another's query results is one of the most common integration-test flakes. See [Integration Testing](../03-integration-testing/middle.md) and [Test Data Management](../11-test-data-management/middle.md) for the full isolation toolkit.

## Core Concept 5 -- Non-Determinism: Random, Time, Iteration Order, Locale

The test reads a source of variability the team forgot to control.

**Unseeded randomness** — seed it:

```python
# ❌ random.random() differs every run
# ✅
rng = random.Random(42)
data = [rng.random() for _ in range(100)]
```

**Real time / dates** — inject a clock instead of calling `now()`:

```go
// ❌ FLAKY: depends on wall-clock; breaks at boundaries / timezones
func IsExpired(t Token) bool { return time.Now().After(t.Expiry) }

// ✅ STABLE: inject the clock so tests control "now"
type Clock interface{ Now() time.Time }
func IsExpired(c Clock, t Token) bool { return c.Now().After(t.Expiry) }
// test uses a fixed clock: fixedClock{at: parse("2026-01-01T00:00:00Z")}
```

**Map / set iteration order** — don't assert on it:

```go
// ❌ FLAKY: Go randomizes map iteration order
for k := range m { result = append(result, k) }
assert.Equal(t, []string{"a","b","c"}, result)

// ✅ STABLE: sort before asserting, or compare as a set
sort.Strings(result)
assert.Equal(t, []string{"a","b","c"}, result)
```

**Locale / timezone** — pin them: set `TZ=UTC` and a fixed locale in the test environment so number/date formatting is stable across machines.

> The unifying fix: **push every non-deterministic input behind an injectable seam** — clock, RNG, locale — so the test controls it. This is prevention-by-design; you'll formalize it at the senior tier.

## Core Concept 6 -- External Dependencies, Concurrency & Resource Leaks

**External dependencies.** A unit test that calls a real API, DNS, or third-party service will flake whenever the network does — and that failure is not your bug. Make such tests **hermetic** by stubbing the dependency (see [Test Doubles](../10-test-doubles-mocks-fakes/middle.md)). Reserve real-network calls for a small, clearly-labeled E2E layer (see [End-to-End Testing](../04-end-to-end-testing/middle.md)).

**Concurrency / real races.** A test that fails ~1-in-N runs with no obvious pattern often points at a genuine data race — sometimes in the *test*, sometimes in the *product code*. Run with a race detector (`go test -race`, ThreadSanitizer, Java's `-Djava.util.concurrent` stress tools). The `concurrency-patterns` skill covers synchronizing shared state correctly. Crucially: don't assume it's the test's fault — investigate whether the product is actually racy.

**Resource leaks / exhaustion.** Tests that pass early in the run and fail late — "address already in use," "too many open files," OOM — are leaking ports, file descriptors, connections, or memory. **Fix:** close everything in teardown (`defer`/`try-with-resources`/fixtures), bind to ephemeral ports (`:0`), and bound connection pools.

## Core Concept 7 -- Detection & Measurement

You cannot manage what you don't measure. Stop guessing whether a test is flaky — *prove* it.

**Re-run to detect (not to hide).** Run the suite or a suspect test many times:

```bash
go test -run TestOrder -count=100        # Go: run 100 times
pytest tests/test_orders.py --count=100  # pytest-repeat
```

If it fails some of the time, it's flaky. This is using reruns *diagnostically* — the opposite of using them to mask failures (see senior tier on retries).

**Flakiness rate as a metric.** Track, per test, `failures / total runs` over a window. A test failing 2% of runs has a 2% flakiness rate. This number, trended over time, tells you whether reliability is improving.

**Flaky-test detection in CI.** Mature setups detect flakiness by re-running *failed* tests once and flagging any test that flips fail→pass as flaky — recording it, not hiding it. Tooling that does this includes:

- `pytest-rerunfailures` (Python), Maven Surefire / Gradle `retry` plugins (JVM) — re-run on failure *and surface that a retry happened*.
- `go test -count=N` and CI scripts for loop-detection.
- Platform tools: **Datadog Test Optimization**, **BuildPulse**, **Gradle Enterprise/Develocity flaky detection**, and Google's internal flaky-test infrastructure — they aggregate fail-then-pass events into dashboards and per-test flakiness scores.

The non-negotiable rule: **reruns are for *identifying* flakiness, never for silently making CI green.** If a test needed a rerun to pass, that fact must be recorded and visible.

## Real-World Examples

- **Shuffle exposes the rot.** A team turns on `go test -shuffle=on` and 14 previously-green tests start failing — all were order-dependent, propped up by alphabetical run order. The suite was lying for months.
- **The race detector earns its keep.** A test flaked 1-in-200. `-race` revealed an unsynchronized map write in *production* code. The flaky test had been catching a real concurrency bug nobody believed.
- **TZ=UTC saves the build.** A date-formatting test passed in CI (UTC) and failed for an engineer in UTC+9. Pinning `TZ=UTC` everywhere — local and CI — ended a recurring "works on my machine" argument.

## Common Mistakes

- **Bumping the sleep instead of polling.** A slower flaky test is still flaky.
- **Cleaning up in the test body, not teardown.** If the test fails mid-way, cleanup is skipped and the next test inherits the mess. Use fixtures/`defer`/`finally`.
- **Asserting on unordered collections** (maps, sets, parallel results) as if they were ordered.
- **Blaming the test for a real race.** Run `-race` before deciding the product is fine.
- **Mocking the clock in one place, reading `now()` in another.** Inject it everywhere or the flake survives.
- **Calling reruns a "fix."** They're detection, not a cure.

---

## Apply it

1. Find a real component where **Flaky Tests & Reliability** affects an interface or dependency.
2. Write two plausible choices and the constraint that favors each one.
3. Make the smallest reversible change at that boundary.
4. Exercise the component alone, then exercise the integrated flow.
5. Keep the decision note with the evidence that selected the option.

## Verify your work

- A focused check proves the local behavior.
- An integrated check proves callers and dependencies still agree.
- Logs, traces, compiler output, or benchmarks expose the boundary.
- Reverting the change restores the previous behavior without unrelated edits.

## Review questions

- Which boundary is most affected by Flaky Tests & Reliability?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
