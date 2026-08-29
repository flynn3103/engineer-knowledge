# Unit Testing — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Unit Testing** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Testing](../README.md) → Unit Testing
>
> *Your first safety net: prove one piece of code does what you claim, in milliseconds, every time.*

---

## Core Concept 1 — What a Unit Test Actually Is

A unit test has four non-negotiable properties:

1. **Isolated** — it tests one unit, not the whole app. If the database is down, your unit test should still pass.
2. **Fast** — milliseconds. A thousand of them should finish in seconds, not minutes.
3. **Deterministic** — it passes or fails for the same reason every time. No "passes on my machine," no "fails every third run."
4. **Self-checking** — it asserts the result automatically. You never read the output by eye to decide pass/fail.

The fastest way to recognize a *non*-unit test is to look for these:

```text
❌ Opens a real database connection
❌ Makes an HTTP request to a real server
❌ Reads or writes a file on disk
❌ Calls time.Now() / new Date() and depends on the result
❌ Sleeps, waits for a timer, or depends on thread scheduling
```

Any of those make the test slow, flaky, or environment-dependent — the opposite of a unit test. (How to *replace* those dependencies in a test is the job of [test doubles](../10-test-doubles-mocks-fakes/), covered later.)

A useful first rule: **if a function takes inputs and returns outputs with no side effects, it is the easiest thing in the world to unit-test.** Pure functions are where you start.

```go
// Easy to test: input in, output out, nothing external.
func Discount(price, percentOff float64) float64 {
    return price * (1 - percentOff/100)
}
```

---

## Core Concept 2 — Your First Test (AAA)

Every clean test has three phases. The pattern is called **Arrange-Act-Assert (AAA)** (some teams say **Given-When-Then** — same idea):

- **Arrange** — set up the inputs and the thing under test.
- **Act** — call the one method you're testing.
- **Assert** — check the result.

Here it is in Go:

```go
package pricing

import "testing"

func TestDiscount_TakesPercentOff(t *testing.T) {
    // Arrange
    price := 200.0
    percentOff := 25.0

    // Act
    got := Discount(price, percentOff)

    // Assert
    want := 150.0
    if got != want {
        t.Errorf("Discount(%v, %v) = %v; want %v", price, percentOff, got, want)
    }
}
```

The same test in Python with `pytest`:

```python
from pricing import discount

def test_discount_takes_percent_off():
    # Arrange
    price, percent_off = 200.0, 25.0
    # Act
    result = discount(price, percent_off)
    # Assert
    assert result == 150.0
```

And in JavaScript/TypeScript with Jest or Vitest:

```ts
import { discount } from "./pricing";

describe("discount", () => {
  it("takes the percentage off the price", () => {
    // Arrange
    const price = 200, percentOff = 25;
    // Act
    const result = discount(price, percentOff);
    // Assert
    expect(result).toBe(150);
  });
});
```

Notice the shape is identical across languages. The tool changes; the discipline doesn't. Keep a blank line between the three phases so the structure is visible at a glance.

---

## Core Concept 3 — Naming Tests as Specifications

A test name should read like a sentence describing the behavior. When the test fails, the **name alone** should tell you what broke — without opening the test body.

Compare:

```text
❌ TestDiscount1
❌ test_it_works
❌ testCalc

✅ TestDiscount_TakesPercentOffPrice
✅ test_discount_of_100_percent_returns_zero
✅ "returns the original price when percentOff is 0"
```

A name that reads as a specification follows a pattern like **`Method_Scenario_ExpectedResult`** or **`it("does X when Y")`**. Examples:

```java
@Test
void withdraw_failsWhenBalanceIsInsufficient() { ... }

@Test
void parse_returnsErrorForEmptyInput() { ... }
```

Your growing list of test names becomes living documentation of what the code is supposed to do. Run the suite with verbose output and you should be able to read the behavior of the whole module like a checklist.

---

## Core Concept 4 — One Logical Assertion per Test

Each test should verify **one behavior**. That doesn't mean literally one `assert` line — it means one *reason to fail*. If a test can fail for three unrelated reasons, a failure tells you almost nothing.

```python
# ❌ Three behaviors crammed into one test — which one broke?
def test_user():
    u = create_user("ann", "ann@x.com")
    assert u.name == "ann"
    assert u.email == "ann@x.com"
    assert u.is_active is True
    assert u.created_at is not None
```

```python
# ✅ One behavior per test — a failure points straight at the cause
def test_create_user_sets_name():
    assert create_user("ann", "ann@x.com").name == "ann"

def test_create_user_starts_active():
    assert create_user("ann", "ann@x.com").is_active is True
```

It's fine for one logical assertion to span several lines (e.g. checking all fields of one returned object). The rule is about **conceptual focus**, not line count. When you see a test with checks on five unrelated things, that's a smell called *assertion roulette* — covered at the senior level.

---

## Core Concept 5 — Testing the Unhappy Path

Beginners test that code works when everything is fine. The bugs that reach production live in the cases you *didn't* test: empty input, zero, negative numbers, nulls, the maximum value, the error branch.

For every function, ask: **what are the boundaries and the failure cases?**

```go
func TestDiscount_HundredPercentIsFree(t *testing.T) {
    if got := Discount(50, 100); got != 0 {
        t.Errorf("100%% off should be free; got %v", got)
    }
}

func TestDiscount_ZeroPercentLeavesPriceUnchanged(t *testing.T) {
    if got := Discount(50, 0); got != 50 {
        t.Errorf("0%% off should not change price; got %v", got)
    }
}
```

And the error path — in Python:

```python
import pytest
from bank import Account

def test_withdraw_more_than_balance_raises():
    acct = Account(balance=100)
    with pytest.raises(InsufficientFundsError):
        acct.withdraw(150)
```

A function with three branches (normal, empty, error) needs at least three tests. The happy path alone is a comfortable illusion.

---

## Real-World Examples

**1. A validation helper.** You write `is_valid_email(s)`. The happy-path test (`"a@b.com"` → true) is obvious. The bugs hide in `""`, `"a@"`, `"@b.com"`, `"a@b@c"`, and a 10,000-character string. Each becomes a one-line test; together they pin the function's real contract.

**2. A bug report becomes a test.** A user reports that a 100% discount charges the full price. Before fixing, you write `TestDiscount_HundredPercentIsFree`. It fails (red). You fix the code. It passes (green). Now that bug **can never come back silently** — the test guards it forever. This is the single most valuable habit a junior can build.

**3. Refactoring with confidence.** You want to rewrite a messy `discount` function. With tests in place, you change the code and rerun: still green means behavior is preserved. Without tests, you're guessing. Tests turn "I think this still works" into "I know this still works."

---

## Common Mistakes

| Mistake | Why it hurts | Fix |
|---|---|---|
| Only testing the happy path | Real bugs are in edge/error cases | Test empty, zero, null, max, and the error branch |
| Vague names (`test1`, `testWorks`) | A failure tells you nothing | Name = `Method_Scenario_Result` |
| Reading output by eye | Not self-checking; not repeatable | Always use an assertion |
| One giant test for everything | Can't tell what broke | One behavior per test |
| Tests that hit a DB or network | Slow and flaky — not unit tests | Test pure logic; isolate dependencies later |
| Depending on `time.Now()` / random | Non-deterministic, fails randomly | Pass time/seed in as a parameter |

---

## Apply it

1. Choose one small, known input for **Unit Testing**.
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

- What problem does Unit Testing solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
