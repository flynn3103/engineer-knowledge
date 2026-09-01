# Test Doubles: Mocks & Fakes — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Test Doubles: Mocks & Fakes** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Testing](../README.md) → Test Doubles: Mocks & Fakes
>
> *Stand-ins for the real thing — so your test can run fast, every time, without touching a database or the network.*

---

## Core Concept 1 — Why Test Doubles Exist

A real dependency causes three problems in a test:

1. **Slow.** A database query or HTTP call is thousands of times slower than an in-memory function call. A suite of 2,000 tests that each hit a real service takes minutes; with doubles it takes a second.
2. **Nondeterministic.** The external API might be down, return different data tomorrow, or rate-limit you. `time.Now()` returns a different value every run. `random()` is, well, random. A flaky test you can't trust is worse than no test.
3. **Hard to control.** To test "what happens when the payment is declined?" you'd need to actually trigger a decline. With a double you just say "pretend this call returns *declined*" — instantly, reliably.

Test doubles solve all three by giving you a fast, deterministic, fully controllable stand-in. That's the entire justification. If a real object is already fast, deterministic, and easy to control (a pure helper function, a value object), **use the real thing** — don't double it.

```
   Real world (in production)          In your test
  ┌────────────┐   ┌─────────┐       ┌────────────┐   ┌──────────────┐
  │  Your code │──▶│ Real DB │       │  Your code │──▶│  Test double │
  │  (the SUT) │   │ network │       │  (the SUT) │   │ fast • exact │
  └────────────┘   └─────────┘       └────────────┘   └──────────────┘
```

---

## Core Concept 2 — The Five Doubles, Named Precisely

People say "mock" for all of these, which is wrong and causes real confusion in code review. Here is the precise distinction:

- **Dummy** — Passed to satisfy a parameter, but never called on the path you're testing. Example: a `Logger` you must pass to a constructor, but the method under test never logs.
- **Stub** — Returns canned data. "When `getUser(7)` is called, return this fixed `User`." It pushes a known input into the SUT. A stub has **no assertions of its own**.
- **Spy** — A stub *plus* a notebook. It returns canned data **and** records what it received ("I was called twice, with these arguments"). The test reads that notebook afterward.
- **Mock** — Set up *in advance* with expectations: "you **must** call `send()` exactly once with this email." The mock itself **verifies** the interaction and fails the test if it didn't happen as specified.
- **Fake** — A genuine working implementation with a shortcut. An in-memory repository that actually stores and retrieves objects (in a map), or an in-memory SQLite instead of production Postgres. It *behaves* correctly; it just isn't production-grade.

The crucial split for now: **stub/spy/fake feed data and let you check the result** (state); **mock asserts that a specific call happened** (behavior). More on that distinction in the middle level.

---

## Core Concept 3 — Your First Stub

Say we have a `Greeter` that fetches a user's name from a repository and builds a greeting. The repository normally hits a database. In the test we replace it with a **stub** that returns a fixed name.

Python, using `unittest.mock`:

```python
from unittest.mock import Mock

def greet(repo, user_id):
    name = repo.get_name(user_id)
    return f"Hello, {name}!"

def test_greet_uses_the_repository_name():
    # Arrange: a stub that returns a canned answer
    repo = Mock()
    repo.get_name.return_value = "Ada"      # canned answer

    # Act
    message = greet(repo, user_id=7)

    # Assert on the RESULT (state verification)
    assert message == "Hello, Ada!"
```

We never touched a database. The stub `repo` answers `get_name` with `"Ada"` no matter what, so the test is instant and deterministic. Notice the assertion is about the **returned string** — the output of our code — not about the stub.

> `unittest.mock.Mock` is a single flexible object that can act as a stub, spy, or mock depending on how you use it. Naming it `repo` (a stub) rather than `mock` keeps your intent clear.

---

## Core Concept 4 — A Stub vs a Mock

This is the single most important distinction in the whole topic. Same scenario, two styles:

**Stub — assert on the result (state):**

```python
def test_with_a_stub():
    repo = Mock()
    repo.get_name.return_value = "Ada"
    assert greet(repo, 7) == "Hello, Ada!"     # I check the OUTPUT
```

**Mock — assert on the interaction (behavior):**

```python
def test_with_a_mock():
    repo = Mock()
    repo.get_name.return_value = "Ada"
    greet(repo, 7)
    repo.get_name.assert_called_once_with(7)    # I check the CALL happened
```

The stub test says *"given this name, the greeting is correct."* The mock test says *"my code called `get_name` once, with `7`."*

For a function whose **output** is what matters (like `greet`), the **stub** version is better: it survives refactoring and actually checks the thing users care about (the greeting). Use a mock only when the *call itself* is the point — e.g. "we must send exactly one confirmation email." Reaching for mocks by default leads to brittle tests, a trap explored at the senior level.

---

## Core Concept 5 — Injecting the Dependency

You can only swap in a double if the code lets you *pass the collaborator in*. This is **dependency injection**, and it's the enabler for everything here.

**Hard to test — the dependency is created inside:**

```python
class OrderService:
    def __init__(self):
        self.db = PostgresDatabase()     # hard-wired; a test can't replace it
```

**Easy to test — the dependency is passed in:**

```python
class OrderService:
    def __init__(self, db):              # injected
        self.db = db

# Production:
service = OrderService(PostgresDatabase())
# Test:
service = OrderService(fake_in_memory_db)   # swap in a fake/stub
```

The second version lets the test hand `OrderService` any stand-in it likes. Whenever something is awkward to test, the first question is usually "is this dependency injected?" The [dependency-injection skill](../unit-testing/junior.md) goes deeper on the techniques.

---

## Real-World Examples

- **Payment declined.** Stub the payment gateway to return `DECLINED`, then assert your checkout shows the right error — without ever making a real charge.
- **Time-sensitive logic.** A "token expires after 1 hour" rule is impossible to test with the real clock unless you wait an hour. Inject a fake clock you can set to any time (middle level).
- **Email confirmation.** Use a *mock* email sender to assert "exactly one welcome email was sent to the new user's address" — here the call **is** the behavior.
- **Flaky third-party API.** Replace the weather API with a fake that returns canned forecasts, so your test passes whether or not the vendor is online.

---

## Common Mistakes

- **Calling everything a "mock."** A stub returns data; a mock verifies calls. Mixing the words muddles design discussions.
- **Stubbing the thing you're testing.** Doubles replace *collaborators*, never the SUT itself. If you stubbed the code under test, you'd be testing nothing.
- **Asserting on the stub instead of the result.** `assert repo.get_name.return_value == "Ada"` checks the test's own setup, not your code. Assert on what `greet` returned.
- **Doubling fast, pure objects.** No need to stub a `Money` value object or a pure formatter — just use the real one.
- **Forgetting determinism.** A "double" that still reads the real clock or real random source isn't controlling the nondeterminism it was supposed to.

---

## Apply it

1. Choose one small, known input for **Test Doubles: Mocks & Fakes**.
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

- What problem does Test Doubles: Mocks & Fakes solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
