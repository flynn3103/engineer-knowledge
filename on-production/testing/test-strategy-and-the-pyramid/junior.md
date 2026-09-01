# Test Strategy & the Pyramid — Junior

<!-- level-focus -->
At junior level, focus on this question:

> How can I apply **Test Strategy & the Pyramid** in one small example and prove the result?

Use the smallest realistic scenario that exposes the decision and its failure behavior.
> **Roadmap:** [Testing](../README.md) → Test Strategy & the Pyramid
> *Why a test suite has layers, and why most of your tests should live at the bottom.*

---

## Core Concept 1 -- The one question a test strategy answers

A *test strategy* is not a tool or a framework. It is a plan that answers one question:

> **What do we test, at what level, and why?**

Without a plan, people test "what is easy to test" or "what they happened to think of." That produces suites that are slow, full of holes, and painful to maintain. A strategy makes the choice on purpose.

The first thing to get right is *level*. The same behaviour can often be checked at more than one level — and the level you pick changes how fast the test runs, how realistic it is, and how clearly it tells you what broke.

## Core Concept 2 -- The three levels

Start with three classic levels, from smallest to largest.

**Unit** — one function or class, by itself. No real database, no network, no clock you can't control.

```python
def discount(price, percent):
    return price - price * percent / 100

def test_discount():
    assert discount(100, 10) == 90   # runs in microseconds
```

**Integration** — your code plus one real collaborator, usually I/O: a database, a file, a queue, another service.

```python
def test_save_order_persists_to_db(db):
    repo = OrderRepository(db)          # real database connection
    repo.save(Order(id=1, total=90))
    assert repo.get(1).total == 90      # round-trips through SQL
```

**End-to-end (E2E)** — the whole system running, driven like a user.

```text
1. Start the app + database + frontend.
2. Open a browser, log in, add item to cart, check out.
3. Assert the confirmation page shows "Order #1234 placed".
```

Each step up adds *more real stuff*: more code exercised, more wiring proven, more realistic. It also adds *more cost*: more setup, more time, more ways to break for reasons unrelated to your change.

## Core Concept 3 -- The pyramid shape

Mike Cohn drew this in his 2009 book *Succeeding with Agile*. The widths show **how many tests of each kind you should have.**

```text
            /\
           /  \         E2E  -- very few, slow, realistic
          /----\
         /      \       Integration -- some, medium speed
        /--------\
       /          \     Unit -- many, fast, focused
      /____________\
```

The pyramid is **bottom-heavy on purpose**: most of your tests are cheap fast unit tests, a moderate number are integration tests, and only a few precious E2E tests cover the most important journeys.

Why not a rectangle (equal numbers everywhere)? Because the upper levels are expensive — in time, in flakiness, in maintenance. A test you can only afford a few of is a test you should *spend on the things that matter most*, not on every edge case.

## Core Concept 4 -- Why fast tests win

The deciding factor is the **feedback loop**: how quickly a failing test tells you *what* is wrong.

| | Unit | Integration | E2E |
|---|---|---|---|
| Typical speed | < 10 ms | 50 ms – 2 s | 5 s – minutes |
| When it fails it says... | "Line 42 returned 91, expected 90" | "The DB query is wrong" | "Something on the checkout page is wrong" |
| How often you can run it | every save | every commit | nightly / pre-merge |

A unit test fails in milliseconds and points at the exact line. An E2E test fails in minutes and points at "something, somewhere, in the whole stack." When you are mid-change, the fast precise signal is worth far more — you stay in flow, you fix the right thing, you run it again immediately.

A simple sum makes it concrete. Suppose you want 1,000 tests:

```text
1,000 unit tests   × 5 ms   = 5 seconds   (run on every save)
1,000 E2E tests    × 8 s     = 2.2 hours   (run... almost never)
```

Same count, wildly different usefulness. Speed is not a nice-to-have; it decides whether the suite gets run at all.

## Core Concept 5 -- What goes where

The allocation rule, in one line per level:

- **Business logic and edge cases → unit tests.** Pricing rules, validation, parsing, state machines, "what happens on the boundary." There are many of these and they are cheap, so cover them thoroughly down here.
- **Wiring and I/O → integration tests.** "Does my SQL actually save and load this object?" "Does my HTTP client parse this real response?" A handful per integration point.
- **Critical user journeys → E2E tests.** "Can a user sign up, buy, and get a receipt?" Only the journeys that *must* work. Not every variation — just the spine.

The trap to avoid: testing the *same* logic at multiple levels. If the discount math is fully covered by unit tests, do **not** also write ten E2E tests for discount edge cases. Test each thing **once**, at the **lowest level that can prove it.**

## Real-World Examples

**A login feature.**

- *Unit:* password hashing produces the right hash; "email must contain @" validation rejects `bob`.
- *Integration:* the user repository actually reads/writes the `users` table.
- *E2E:* one test — open the page, type a valid email + password, click Login, land on the dashboard.

Notice: one E2E covers the happy path; the dozens of validation cases live in fast unit tests.

**A shopping cart.** All the "add quantity, apply coupon, recompute total" math is unit-tested (dozens of cases). Integration tests confirm the cart saves to the DB. A single E2E proves a real user can check out.

## Common Mistakes

- **Everything through the UI.** Writing all tests as browser/E2E tests because "that's how a user uses it." Result: a 40-minute, flaky suite. (This is the *ice-cream cone* anti-pattern — covered in [middle.md](middle.md).)
- **No strategy — test what's easy.** You end up with tests for getters and none for the gnarly pricing rule.
- **Duplicating coverage.** The same edge case tested as unit *and* integration *and* E2E. Slow, and three places to update when the rule changes.
- **Skipping the bottom.** Jumping straight to integration/E2E because "those feel more real." You lose the fast feedback that makes daily work pleasant.

---

## Apply it

1. Choose one small, known input for **Test Strategy & the Pyramid**.
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

- What problem does Test Strategy & the Pyramid solve in the example?
- Which input changes the observed result, and why?
- What is the smallest useful success check?
- Which beginner mistake would your evidence catch?
