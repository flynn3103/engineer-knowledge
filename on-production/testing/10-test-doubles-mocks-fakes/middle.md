# Test Doubles: Mocks & Fakes — Middle

<!-- level-focus -->
At middle level, focus on this question:

> Where does **Test Doubles: Mocks & Fakes** belong in a maintainable component, and which trade-off selects the design?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Testing](../README.md) → Test Doubles: Mocks & Fakes
>
> *State or behavior? Detroit or London? The choices here decide whether your tests survive a refactor or shatter on contact.*

---

## Core Concept 1 — State Verification vs Behavior Verification

There are two fundamentally different things a test can assert.

**State verification** — act, then check the *resulting state or output*:

```python
def test_deposit_increases_balance():
    account = Account(balance=100)
    account.deposit(50)
    assert account.balance == 150        # check resulting STATE
```

**Behavior verification** — act, then check that *a particular call happened*:

```python
def test_deposit_writes_to_the_ledger():
    ledger = Mock()
    account = Account(balance=100, ledger=ledger)
    account.deposit(50)
    ledger.record.assert_called_once_with(amount=50)   # check the INTERACTION
```

State verification (stubs/fakes support it) treats your code as a black box: *given this, I expect that result.* Behavior verification (mocks do it) reaches inside: *I expect you to make this specific call.*

The consequence for **brittleness** is profound. State tests only break when the *observable result* changes — exactly when you'd want them to. Behavior tests break whenever the *implementation* changes, even if the result is identical. If you rename `record` to `append`, or batch two ledger writes into one, the behavior test fails though nothing users care about changed. **Prefer state verification** unless the interaction genuinely *is* the contract.

---

## Core Concept 2 — The Spy: A Stub That Remembers

A spy is a stub that also records how it was called, so you can inspect afterwards. The key difference from a mock: a spy **records silently and lets you assert at the end**, whereas a mock has expectations **set up front** and verifies itself. Spies make behavior verification readable without front-loaded ceremony.

Go, hand-rolled spy (Go's idiomatic style — small interface, struct that records):

```go
type Notifier interface {
    Notify(userID string, msg string) error
}

// Spy: implements Notifier AND records every call.
type spyNotifier struct {
    calls []struct {
        userID, msg string
    }
}

func (s *spyNotifier) Notify(userID, msg string) error {
    s.calls = append(s.calls, struct{ userID, msg string }{userID, msg})
    return nil
}

func TestWelcomeSendsOneNotification(t *testing.T) {
    spy := &spyNotifier{}
    svc := NewSignupService(spy)

    svc.Register("u-1")

    if len(spy.calls) != 1 {
        t.Fatalf("want 1 notification, got %d", len(spy.calls))
    }
    if spy.calls[0].userID != "u-1" {
        t.Errorf("notified wrong user: %s", spy.calls[0].userID)
    }
}
```

Hand-rolling a spy as a small struct is idiomatic Go and beats a heavyweight mocking framework for most cases — it's explicit and refactor-friendly.

---

## Core Concept 3 — The Fake: A Working In-Memory Implementation

A fake is the most underused and most valuable double. Instead of canned-per-call answers, it's a *real implementation* with a shortcut — so it behaves correctly across an entire test, no matter what sequence of calls you make.

An in-memory repository fake (Python):

```python
class InMemoryUserRepo:
    """A FAKE: real save/get behavior, backed by a dict instead of a DB."""
    def __init__(self):
        self._store = {}

    def save(self, user):
        self._store[user.id] = user

    def get(self, user_id):
        return self._store.get(user_id)

def test_register_then_fetch_round_trips():
    repo = InMemoryUserRepo()           # one fake, used like the real thing
    service = SignupService(repo)

    service.register(id=7, name="Ada")

    assert repo.get(7).name == "Ada"    # STATE verification on a real-ish object
```

Why fakes beat a pile of stubs: a stub answers one canned value; a fake **stays consistent** — what you save, you can get back; deletes actually delete. You can write a multi-step test (register → update → fetch) against it. Maintain the fake *alongside* the real repository, ideally behind the same interface, and run the **same contract test suite** against both to keep them honest.

---

## Core Concept 4 — Classical (Detroit) vs Mockist (London)

Two schools, named for where they emerged:

- **Classical / Detroit (Beck, Fowler).** Use real objects wherever practical. Reach for a double **only** at *awkward* collaborators — slow, nondeterministic, side-effecting, or expensive ones (DB, network, clock). Prefer **fakes and real objects** over mocks. Verify **state**.
- **Mockist / London (Freeman, Pryce — *Growing Object-Oriented Software, Guided by Tests*).** Mock **every** collaborator of the unit, so each test isolates a single class. Drives design "outside-in": you discover the interfaces a class *needs* by mocking them. Verify **behavior**.

| | Classical (Detroit) | Mockist (London) |
|---|---|---|
| What to mock | Awkward boundaries only | Every collaborator |
| Verifies | State / output | Interactions |
| Refactor safety | High — tests survive internal changes | Lower — tests coupled to call structure |
| Drives design? | Less directly | Strongly (outside-in TDD) |
| Failure localization | Broader (cluster of objects) | Sharp (one class) |

The modern consensus leans **classical**: mock at architectural boundaries, prefer fakes, and follow two rules that cut across both schools — **"don't mock what you don't own"** and **"prefer fakes/real objects to mocks."** London-style isolation is a powerful *design* tool during TDD, but a suite where every collaborator is mocked tends to become brittle (see senior level). Most teams use a blend: London thinking to *discover* interfaces, Detroit verification to *keep* the resulting tests robust.

---

## Core Concept 5 — Faking the Clock and Randomness

The clock and the random source are the two classic sources of nondeterminism. **Never `sleep` in a test, and never let production read the wall clock directly.** Inject them.

**The clock** — inject a time source instead of calling `time.Now()`:

```go
type Clock interface{ Now() time.Time }

type realClock struct{}
func (realClock) Now() time.Time { return time.Now() }

// Fake clock you control:
type fakeClock struct{ t time.Time }
func (c *fakeClock) Now() time.Time { return c.t }

func TestTokenExpiresAfterOneHour(t *testing.T) {
    clk := &fakeClock{t: time.Date(2026, 1, 1, 12, 0, 0, 0, time.UTC)}
    tok := IssueToken(clk)

    clk.t = clk.t.Add(61 * time.Minute)   // "advance time" instantly
    if !tok.IsExpired(clk) {
        t.Fatal("token should be expired after 61 minutes")
    }
}
```

A one-hour-expiry rule is now tested in microseconds, deterministically.

**Randomness** — inject the source (or a seed) so "random" becomes reproducible:

```python
import random

def pick_winner(entrants, rng):
    return entrants[rng.randrange(len(entrants))]

def test_winner_is_deterministic_with_a_seeded_rng():
    rng = random.Random(42)              # injected, seeded → reproducible
    assert pick_winner(["a", "b", "c"], rng) == "c"   # same every run
```

The rule: **anything nondeterministic becomes a dependency you inject.** Then the test controls it.

---

## Core Concept 6 — Faking HTTP and the Filesystem

**HTTP** — don't call the real API; stand up a fake server. Go's `httptest` (in the standard library) is the model:

```go
func TestClientParsesResponse(t *testing.T) {
    srv := httptest.NewServer(http.HandlerFunc(
        func(w http.ResponseWriter, r *http.Request) {
            w.Write([]byte(`{"temp_c": 21}`))   // canned response
        }))
    defer srv.Close()

    c := NewWeatherClient(srv.URL)         // point the client at the fake
    got, _ := c.Temperature("London")
    if got != 21 {
        t.Errorf("want 21, got %v", got)
    }
}
```

`httptest` runs a real local server, so you exercise your *actual* HTTP code (URL building, headers, JSON decoding) against canned responses. In the JVM/JS world, **WireMock** plays the same role. This is far better than mocking your HTTP client object, because it tests the real serialization path.

**The filesystem** — inject a filesystem abstraction (Go's `io/fs`, an in-memory `fs` in Node, `pyfakefs` in Python) so tests never touch a real disk, leave no temp files, and run in parallel without collisions.

> Caveat: faking an external HTTP API still tests *your model* of that API, which may be wrong. The honest answer is **contract testing** ([05-contract-testing](../05-contract-testing/middle.md)) — covered in the senior tier under "don't mock what you don't own."

---

## Real-World Examples

- **Subscription renewal.** Inject a fake clock; advance it 30 days; assert the renewal job fires — instead of waiting a month.
- **Retry with backoff.** Inject the clock so the test can "fast-forward" through backoff delays in microseconds (see the `retry-pattern` skill).
- **Shuffling a deck.** Inject a seeded RNG so a "fair shuffle" test is reproducible and debuggable.
- **Order service tests.** Run the *same* contract suite against `InMemoryOrderRepo` (fake) and `PostgresOrderRepo` (real) to prove the fake stays faithful.

---

## Common Mistakes

- **Behavior-verifying a pure result.** Asserting `ledger.record.assert_called` when you could assert `account.balance == 150`. Prefer the state check.
- **`sleep()` in tests.** It's slow and still flaky. Inject a clock and advance it.
- **Mocking your own HTTP client object** instead of using `httptest`/WireMock — you skip the real serialization code, which is where bugs live.
- **A fake that lies.** An in-memory repo whose `save` silently ignores duplicates while the real DB errors. Pin both with a shared contract test.
- **Going full mockist by default.** Mocking every collaborator gives sharp failure localization but a brittle suite. Mock awkward boundaries, fake the rest.

---

## Apply it

1. Find a real component where **Test Doubles: Mocks & Fakes** affects an interface or dependency.
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

- Which boundary is most affected by Test Doubles: Mocks & Fakes?
- What constraint would make you choose the alternative design?
- How would you isolate a local defect from an integration defect?
- What evidence shows that the change remains maintainable?
