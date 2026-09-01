# Flaky Tests & Reliability — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Flaky Tests & Reliability** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Testing](../README.md) → Flaky Tests & Reliability
> *A test that passes today and fails tomorrow on the exact same code is not a flaky test — it is a broken test, and it is quietly destroying your team's trust.*

---

## Core Concept 1 -- What "Flaky" Actually Means

A test is flaky when **the same code, run twice, gives different test results.**

```
Run 1:  test_user_sees_dashboard  ✅ PASS
Run 2:  test_user_sees_dashboard  ❌ FAIL    ← nothing changed!
Run 3:  test_user_sees_dashboard  ✅ PASS
```

The key word is **non-deterministic**. A test that always fails isn't flaky — it's just failing, and that's honest. A test that always passes isn't flaky — it's reliable. Flaky is the in-between, "sometimes" state. That "sometimes" is the danger, because it means you cannot tell from a red result whether something is actually broken.

A good test answers one question precisely: *is the code correct?* A flaky test answers a different, useless question: *did I get lucky this time?*

> **The core slogan of this entire topic: a flaky test is a broken test.** It doesn't matter that it passes most of the time. A test you can't trust is worth less than no test at all, because it costs you time and confidence while giving you nothing reliable in return.

## Core Concept 2 -- Why Flakiness Is Existential: Trust Erosion

Here is the part juniors underestimate. The damage from a flaky test is **not the failure itself.** It's what the failure teaches your team.

Watch the chain of events:

1. A flaky test fails on someone's correct PR.
2. They learn: "red doesn't always mean I broke something."
3. So next time CI is red, they re-run instead of investigating.
4. Re-running becomes a reflex. **Red stops meaning "stop."**
5. One day, a *real* bug turns the suite red. Everyone re-runs out of habit. The bug ships.

This is **trust erosion**, and it's why flakiness is existential. The entire value of a test suite is the promise: **"if it's green, you're safe; if it's red, stop and look."** A flaky test breaks that promise. Once people don't believe red, the suite is decoration. You're paying CI bills and writing tests for nothing.

> **Trust is the asset.** Tests don't protect code directly — they protect the *trust* that lets a team move fast without fear. Protect that trust like it's production data.

This is why a single ignored flaky test is dangerous out of all proportion to its size. It's not "one annoying test." It's one crack that trains everyone to ignore cracks.

## Core Concept 3 -- The Most Common Cause: Waiting on a Sleep, Not a Condition

The number-one cause of flaky tests you'll meet as a junior is **timing**: the test asks for something that happens *asynchronously* (in the background, on another thread, after a network call) and then guesses how long to wait.

The bad pattern is a **fixed sleep**:

```python
# ❌ FLAKY: guess that 1 second is "enough"
def test_order_is_processed():
    submit_order(order_id=42)
    time.sleep(1)                       # hope the worker finished by now
    assert get_status(42) == "processed"
```

Why is this flaky? `sleep(1)` is a **guess**. On your fast laptop the worker finishes in 200 ms, so the test passes. On a loaded CI machine it takes 1.3 seconds, so the assertion runs *before* the work is done, and the test fails. Same code, different machine speed, different result. Pure flakiness.

Sleeps also have no good answer: too short and it's flaky, too long and your suite crawls. Both are bad.

The fix is to **poll for the actual condition** — repeatedly check until the thing you want is true, up to a maximum timeout:

```python
# ✅ STABLE: wait for the real condition, not a guessed duration
def wait_until(predicate, timeout=5.0, interval=0.05):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(interval)
    raise AssertionError(f"condition not met within {timeout}s")

def test_order_is_processed():
    submit_order(order_id=42)
    wait_until(lambda: get_status(42) == "processed")   # poll, don't guess
    assert get_status(42) == "processed"
```

Now the test waits *exactly as long as needed* and no longer. On a fast machine it returns in 200 ms; on a slow machine it waits up to 5 seconds. It only fails if the work genuinely never completes — which is a *real* failure, the kind you want.

> Rule of thumb: **if you wrote `sleep` in a test, you probably wrote a flaky test.** Replace it with "wait until this condition is true." End-to-end frameworks call this an *explicit wait* (see [End-to-End Testing](../end-to-end-testing/junior.md)).

## Core Concept 4 -- Other Things That Make Tests Flaky

Beyond sleeps, here are the causes you'll bump into early. You'll go deeper at the next tier; for now, just learn to *recognize* them.

- **Randomness without a seed.** A test that generates a random value behaves differently each run.
- **Time and dates.** Tests that use "now" break at midnight, month boundaries, or in a different timezone.
- **Test order / shared state.** Test A leaves data behind that Test B accidentally depends on, so they pass together but fail when run alone or reordered.
- **Real network / external services.** Calling a real API means your test fails when the network hiccups — that's not your bug.
- **Map / set iteration order.** In some languages, iterating a map yields elements in an unpredictable order; asserting a fixed order is flaky.

Here's a quick seeded-random fix you can apply today:

```python
# ❌ FLAKY: unseeded randomness — different data every run
def test_shuffle_keeps_all_items():
    items = generate_random_items()      # different each run
    ...

# ✅ STABLE: seed it so the run is reproducible
def test_shuffle_keeps_all_items():
    rng = random.Random(12345)           # fixed seed → same data every run
    items = [rng.randint(0, 100) for _ in range(10)]
    shuffled = shuffle(items, rng=rng)
    assert sorted(shuffled) == sorted(items)
```

## Core Concept 5 -- What To Do When You Hit a Flaky Test

You *will* hit one. Here's the junior playbook:

1. **Don't just re-run and move on.** That's the reflex that erodes trust. A green-on-rerun is information, not absolution.
2. **Reproduce it.** Run the test many times in a loop. If it fails maybe 1-in-20, you've confirmed flakiness.
   ```bash
   # Run a single test 50 times to surface flakiness
   for i in $(seq 1 50); do pytest tests/test_orders.py::test_order_is_processed -q || echo "FAILED run $i"; done
   ```
   In Go: `go test -run TestOrder -count=50`.
3. **Find the cause** using the list above — most likely a sleep, randomness, time, or shared state.
4. **Fix it or report it.** If you can fix it (sleep→poll, seed the random), do so. If you can't yet, tell a senior — a flaky test is a real bug that needs an owner, not something to silently ignore.
5. **Never disable-and-forget.** If a test must be temporarily turned off, it needs a ticket and an owner (you'll learn this *quarantine* discipline at the senior tier). A disabled test with no follow-up is worse than a flaky one — it's a silent gap.

## Real-World Examples

- **The "just re-run it" Slack culture.** A team has one flaky login test. People post "re-running CI 🤞" daily. Six months later a genuine auth regression ships to production because everyone assumed the red was "the usual flake." The product bug existed for two weeks before anyone trusted the red enough to look.
- **The midnight failure.** A test asserting `created_at == today()` passes all day and fails for engineers in a different timezone whose "today" has already rolled over. The fix: inject a fixed clock instead of reading the real time.
- **Works on my machine.** A test passes locally (fast SSD, no load) and fails in CI (shared, slow, parallel). Classic `sleep`-too-short timing flake. The machine wasn't the problem; the guessed wait was.

## Common Mistakes

- **Re-running until green and calling it fixed.** You hid the symptom; the disease (and the trust damage) remain.
- **Adding `sleep(5)` to "make it pass."** You traded a fast flaky test for a slow flaky test.
- **Assuming flakiness is always the test's fault.** Sometimes the *product* has a real race condition and the flaky test is correctly catching it. (More on this later.)
- **Silently `@skip`-ing the test.** A skipped test with no ticket is a permanent blind spot nobody remembers.
- **Asserting on map/iteration order** when the language doesn't guarantee it. Sort first, or assert on a set.

---

## Apply it

1. Choose one small, known input for **Flaky Tests & Reliability**.
2. Predict the output or observable behavior.
3. Run the smallest example or probe that exercises the concept.
4. Change one input to trigger a failure or boundary case.
5. Explain the evidence using the guide's vocabulary.

## Verify your work

- Record the exact input, command or code path, and output.
- Repeat the probe and confirm the result is consistent.
- Show one expected success and one expected failure.
- Resolve any difference between the prediction and the evidence.

## Review questions

- What problem does Flaky Tests & Reliability solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
